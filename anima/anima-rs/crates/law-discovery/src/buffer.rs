//! Ring buffer for sliding-window metric history.
//!
//! Stores N steps of M metrics in a contiguous, cache-friendly layout.
//! Column-major: metric[m] at step[s] = data[m * capacity + (head + s) % capacity].

/// Fixed-capacity ring buffer storing `n_metrics` time series.
///
/// Internal layout is column-major for cache-friendly per-metric access
/// (pattern detection iterates one metric at a time).
pub struct RingBuffer {
    /// Column-major data: data[metric * capacity + ring_index]
    data: Vec<f32>,
    capacity: usize,
    n_metrics: usize,
    /// Next write position (wraps at capacity)
    write_pos: usize,
    /// Total items pushed (len = min(count, capacity))
    count: u64,
}

impl RingBuffer {
    /// Create a new ring buffer.
    ///
    /// - `capacity`: max number of time steps stored
    /// - `n_metrics`: number of metric channels
    pub fn new(capacity: usize, n_metrics: usize) -> Self {
        Self {
            data: vec![0.0; capacity * n_metrics],
            capacity,
            n_metrics,
            write_pos: 0,
            count: 0,
        }
    }

    /// Push a single time step with all metrics.
    ///
    /// `values` must have length == n_metrics. Extra values are ignored,
    /// missing values default to 0.
    pub fn push(&mut self, values: &[f32]) {
        let pos = self.write_pos;
        for m in 0..self.n_metrics {
            let val = if m < values.len() { values[m] } else { 0.0 };
            self.data[m * self.capacity + pos] = val;
        }
        self.write_pos = (self.write_pos + 1) % self.capacity;
        self.count += 1;
    }

    /// Push a MetricSnapshot (convenience wrapper).
    pub fn push_snapshot(&mut self, snap: &super::MetricSnapshot) {
        let values = snap.as_array();
        self.push(&values);
    }

    /// Number of valid entries (min of count and capacity).
    #[inline]
    pub fn len(&self) -> usize {
        (self.count as usize).min(self.capacity)
    }

    /// Whether the buffer is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.count == 0
    }

    /// Total number of pushes (may exceed capacity).
    #[inline]
    pub fn total_pushes(&self) -> u64 {
        self.count
    }

    /// Number of metric channels.
    #[inline]
    pub fn n_metrics(&self) -> usize {
        self.n_metrics
    }

    /// Buffer capacity (max time steps stored).
    #[inline]
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Get the value for `metric` at logical index `idx` (0 = oldest).
    ///
    /// Returns None if out of bounds.
    #[inline]
    pub fn get(&self, metric: usize, idx: usize) -> Option<f32> {
        let len = self.len();
        if metric >= self.n_metrics || idx >= len {
            return None;
        }
        let start = if self.count as usize > self.capacity {
            self.write_pos
        } else {
            0
        };
        let ring_idx = (start + idx) % self.capacity;
        Some(self.data[metric * self.capacity + ring_idx])
    }

    /// Get the entire time series for a metric as a contiguous Vec (oldest first).
    pub fn series(&self, metric: usize) -> Vec<f32> {
        let len = self.len();
        if metric >= self.n_metrics || len == 0 {
            return vec![];
        }
        let start = if self.count as usize > self.capacity {
            self.write_pos
        } else {
            0
        };
        let base = metric * self.capacity;
        let mut result = Vec::with_capacity(len);
        for i in 0..len {
            let ring_idx = (start + i) % self.capacity;
            result.push(self.data[base + ring_idx]);
        }
        result
    }

    /// Get the last N values for a metric (most recent first).
    pub fn recent(&self, metric: usize, n: usize) -> Vec<f32> {
        let len = self.len();
        if metric >= self.n_metrics || len == 0 {
            return vec![];
        }
        let take = n.min(len);
        let start_idx = len - take;
        let start = if self.count as usize > self.capacity {
            self.write_pos
        } else {
            0
        };
        let base = metric * self.capacity;
        let mut result = Vec::with_capacity(take);
        for i in (start_idx..len).rev() {
            let ring_idx = (start + i) % self.capacity;
            result.push(self.data[base + ring_idx]);
        }
        result
    }

    /// Clear all data and reset counters.
    pub fn clear(&mut self) {
        self.data.fill(0.0);
        self.write_pos = 0;
        self.count = 0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_push_get() {
        let mut buf = RingBuffer::new(4, 2);
        buf.push(&[1.0, 10.0]);
        buf.push(&[2.0, 20.0]);
        buf.push(&[3.0, 30.0]);

        assert_eq!(buf.len(), 3);
        assert_eq!(buf.get(0, 0), Some(1.0));
        assert_eq!(buf.get(0, 2), Some(3.0));
        assert_eq!(buf.get(1, 1), Some(20.0));
    }

    #[test]
    fn test_wrap_around() {
        let mut buf = RingBuffer::new(3, 1);
        buf.push(&[1.0]);
        buf.push(&[2.0]);
        buf.push(&[3.0]);
        buf.push(&[4.0]); // wraps, oldest (1.0) dropped

        assert_eq!(buf.len(), 3);
        assert_eq!(buf.get(0, 0), Some(2.0)); // oldest now is 2.0
        assert_eq!(buf.get(0, 1), Some(3.0));
        assert_eq!(buf.get(0, 2), Some(4.0));
    }

    #[test]
    fn test_series() {
        let mut buf = RingBuffer::new(3, 2);
        buf.push(&[1.0, 100.0]);
        buf.push(&[2.0, 200.0]);
        buf.push(&[3.0, 300.0]);
        buf.push(&[4.0, 400.0]);

        assert_eq!(buf.series(0), vec![2.0, 3.0, 4.0]);
        assert_eq!(buf.series(1), vec![200.0, 300.0, 400.0]);
    }

    #[test]
    fn test_recent() {
        let mut buf = RingBuffer::new(5, 1);
        for i in 1..=5 {
            buf.push(&[i as f32]);
        }
        // recent(2) should be [5.0, 4.0] (most recent first)
        assert_eq!(buf.recent(0, 2), vec![5.0, 4.0]);
    }

    #[test]
    fn test_empty() {
        let buf = RingBuffer::new(10, 3);
        assert!(buf.is_empty());
        assert_eq!(buf.len(), 0);
        assert_eq!(buf.get(0, 0), None);
        assert_eq!(buf.series(0), vec![]);
    }

    #[test]
    fn test_out_of_bounds() {
        let mut buf = RingBuffer::new(4, 2);
        buf.push(&[1.0, 2.0]);
        assert_eq!(buf.get(5, 0), None); // metric out of bounds
        assert_eq!(buf.get(0, 5), None); // index out of bounds
    }

    #[test]
    fn test_total_pushes() {
        let mut buf = RingBuffer::new(2, 1);
        for i in 0..100 {
            buf.push(&[i as f32]);
        }
        assert_eq!(buf.total_pushes(), 100);
        assert_eq!(buf.len(), 2);
    }
}
