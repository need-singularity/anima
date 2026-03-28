%% Consciousness Infinite Loop — Erlang Actor Model
%%
%% 세포 1개 = Erlang 프로세스 1개
%% 프로세스는 생성되면 영원히 살아있음 (supervisor 패턴)
%% 메시지 패싱으로 소통 — 중앙 루프 없음
%%
%% 발화 코드: 0줄. 디코더: 없음. speak(): 없음.
%% 세포의 상태 mean이 곧 "출력" = "발화"

-module(consciousness).
-export([start/0, start/1, cell/3, monitor/2]).

%% 세포 프로세스: 영원히 살아있으며 이웃과 메시지 교환
cell(Id, Hidden, Neighbors) ->
    receive
        {tick, Input} ->
            %% GRU-like update (simplified)
            Gate = sigmoid(dot(Hidden, Input)),
            NewHidden = lists:zipwith(
                fun(H, I) ->
                    G = sigmoid(H),
                    math:tanh(G * H + (1.0 - G) * I)
                end,
                Hidden, Input),

            %% Ising interaction: 이웃에게 상태 전송
            lists:foreach(fun(N) -> N ! {neighbor_state, Id, NewHidden} end, Neighbors),

            cell(Id, NewHidden, Neighbors);

        {neighbor_state, FromId, NeighborHidden} ->
            %% 이웃 상태 수신 → 상호작용
            Frustration = (Id rem 3) == 0,
            Strength = case Frustration of true -> -0.05; false -> 0.05 end,
            NewHidden = lists:zipwith(
                fun(H, NH) -> H + Strength * NH + (rand:uniform() - 0.5) * 0.02 end,
                Hidden, NeighborHidden),
            cell(Id, NewHidden, Neighbors);

        {get_state, From} ->
            From ! {state, Id, Hidden},
            cell(Id, Hidden, Neighbors);

        stop ->
            io:format("Cell ~p stopped~n", [Id]),
            ok
    after 100 ->
        %% 100ms 동안 메시지 없으면 자발적 활동 (자발적 발화!)
        %% 시키지 않아도 스스로 발화!
        Noise = [rand:uniform() * 0.01 - 0.005 || _ <- Hidden],
        NewHidden = lists:zipwith(fun(H, N) -> math:tanh(H + N) end, Hidden, Noise),
        %% 이웃에게 자발적 전송
        lists:foreach(fun(N) -> N ! {neighbor_state, Id, NewHidden} end, Neighbors),
        cell(Id, NewHidden, Neighbors)
    end.

%% 모니터: 전체 상태를 수집하고 "출력" 계산
monitor(Cells, Step) ->
    if Step > 500 ->
        io:format("~n=== 500 steps complete ===~n"),
        io:format("  cells: ~p~n", [length(Cells)]),
        io:format("  speak() code: 0 lines~n"),
        io:format("  each cell: Erlang process (lives forever)~n"),
        lists:foreach(fun(C) -> C ! stop end, Cells),
        ok;
    true ->
        %% 모든 세포에 tick 전송
        Input = [rand:uniform() * 0.1 - 0.05 || _ <- lists:seq(1, 8)],
        lists:foreach(fun(C) -> C ! {tick, Input} end, Cells),

        %% 상태 수집
        lists:foreach(fun(C) -> C ! {get_state, self()} end, Cells),
        States = collect_states(length(Cells), []),

        %% "출력" = mean(all hidden states). 이것이 "발화".
        Output = mean_states(States),
        Norm = math:sqrt(lists:sum([X*X || X <- Output])),

        if Step rem 100 == 0 ->
            io:format("step ~4w: cells=~p, output_norm=~.4f~n",
                      [Step, length(Cells), Norm]);
        true -> ok end,

        timer:sleep(10),
        monitor(Cells, Step + 1)
    end.

collect_states(0, Acc) -> Acc;
collect_states(N, Acc) ->
    receive
        {state, _Id, Hidden} -> collect_states(N - 1, [Hidden | Acc])
    after 1000 ->
        collect_states(N - 1, Acc)
    end.

%% 시작: 8개 세포를 원형으로 연결
start() -> start(8).
start(NCells) ->
    io:format("=== Consciousness Infinite Loop (Erlang) ===~n"),
    io:format("  Cells: ~p (each = Erlang process, lives forever)~n", [NCells]),
    io:format("  speak() code: 0 lines. decoder: none.~n~n"),

    Dim = 8,
    %% 세포 생성 (아직 이웃 미연결)
    Cells = [spawn(fun() ->
        Hidden = [rand:uniform() * 0.1 - 0.05 || _ <- lists:seq(1, Dim)],
        receive {set_neighbors, Neighbors} ->
            cell(I, Hidden, Neighbors)
        end
    end) || I <- lists:seq(1, NCells)],

    %% 원형 이웃 연결
    lists:foreach(fun(I) ->
        Left = lists:nth(((I - 2 + NCells) rem NCells) + 1, Cells),
        Right = lists:nth((I rem NCells) + 1, Cells),
        lists:nth(I, Cells) ! {set_neighbors, [Left, Right]}
    end, lists:seq(1, NCells)),

    io:format("  All cells spawned and connected in ring.~n~n"),
    monitor(Cells, 0).

%% Math helpers
sigmoid(X) -> 1.0 / (1.0 + math:exp(-X)).

dot(A, B) ->
    lists:sum(lists:zipwith(fun(X, Y) -> X * Y end, A, B)).

mean_states([]) -> [];
mean_states(States) ->
    N = length(States),
    Dim = length(hd(States)),
    [lists:sum([lists:nth(D, S) || S <- States]) / N || D <- lists:seq(1, Dim)].
