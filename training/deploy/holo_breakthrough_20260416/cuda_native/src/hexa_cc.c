// HEXA self-hosted compiler — regenerated via `hexa cc --regen`
#include "runtime.c"


// === lexer ===




static HexaIC __hexa_lexer_ic_0 = {0};

HexaVal Token(HexaVal kind, HexaVal value, HexaVal line, HexaVal col) {
    static const char* const _k[] = {"kind", "value", "line", "col"};
    HexaVal _v[] = {kind, value, line, col};
    return hexa_struct_pack_map("Token", 4, _k, _v);
}


HexaVal is_keyword(HexaVal word) {
    if (hexa_truthy(hexa_eq(word, hexa_str("if")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("else")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("match")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("for")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("while")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("loop")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("type")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("struct")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("enum")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("trait")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("impl")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("fn")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("return")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("yield")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("async")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("await")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("let")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("mut")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("const")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("static")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("mod")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("use")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("import")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("pub")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("crate")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("own")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("borrow")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("move")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("drop")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("spawn")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("channel")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("select")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("atomic")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("effect")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("handle")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("resume")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("pure")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("proof")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("assert")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("invariant")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("theorem")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("macro")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("derive")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("where")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("comptime")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("try")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("catch")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("throw")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("panic")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("recover")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("intent")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("generate")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("verify")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("optimize")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("extern")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("break")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("continue")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("dyn")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("scope")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("in")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("do")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("defer")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("typeof")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("guard")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("with")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("as")))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal keyword_kind(HexaVal word) {
    if (hexa_truthy(hexa_eq(word, hexa_str("true")))) {
        return hexa_str("BoolLit");
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("false")))) {
        return hexa_str("BoolLit");
    }
    if (hexa_truthy(hexa_eq(word, hexa_str("import")))) {
        return hexa_str("Use");
    }
    if (hexa_truthy(is_keyword(word))) {
        HexaVal first = hexa_str_to_upper(hexa_to_string(hexa_index_get(hexa_str_chars(word), hexa_int(0))));
        HexaVal rest_parts = hexa_array_new();
        HexaVal chars = hexa_str_chars(word);
        HexaVal i = hexa_int(1);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(chars))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            rest_parts = hexa_array_push(rest_parts, hexa_to_string(hexa_index_get(chars, i)));
            i = hexa_add(i, hexa_int(1));
        }
        return hexa_add(first, hexa_str_join(rest_parts, hexa_str("")));
    }
    return hexa_str("Ident");
    return hexa_void();
}


HexaVal is_ident_start(HexaVal ch) {
    if (hexa_truthy(hexa_bool((ch.tag==TAG_STR && ch.s && isalpha((unsigned char)ch.s[0])) || (ch.tag==TAG_CHAR && isalpha((unsigned char)ch.i))))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(ch, hexa_str("_")))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal is_ident_char(HexaVal ch) {
    if (hexa_truthy(hexa_bool((ch.tag==TAG_STR && ch.s && isalnum((unsigned char)ch.s[0])) || (ch.tag==TAG_CHAR && isalnum((unsigned char)ch.i))))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(ch, hexa_str("_")))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal is_hex_digit(HexaVal ch) {
    if (hexa_truthy(hexa_bool((ch.tag==TAG_STR && ch.s && isdigit((unsigned char)ch.s[0])) || (ch.tag==TAG_CHAR && isdigit((unsigned char)ch.i))))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ch, hexa_str("a"))) || hexa_truthy(hexa_eq(ch, hexa_str("b"))))) || hexa_truthy(hexa_eq(ch, hexa_str("c"))))) || hexa_truthy(hexa_eq(ch, hexa_str("d"))))) || hexa_truthy(hexa_eq(ch, hexa_str("e"))))) || hexa_truthy(hexa_eq(ch, hexa_str("f")))))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ch, hexa_str("A"))) || hexa_truthy(hexa_eq(ch, hexa_str("B"))))) || hexa_truthy(hexa_eq(ch, hexa_str("C"))))) || hexa_truthy(hexa_eq(ch, hexa_str("D"))))) || hexa_truthy(hexa_eq(ch, hexa_str("E"))))) || hexa_truthy(hexa_eq(ch, hexa_str("F")))))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal tokenize(HexaVal source) {
    HexaVal start_col = hexa_void();
    HexaVal esc = hexa_void();
    HexaVal tokens = hexa_array_new();
    HexaVal chars = hexa_str_chars(source);
    HexaVal pos = hexa_int(0);
    HexaVal line = hexa_int(1);
    HexaVal col = hexa_int(1);
    HexaVal total = hexa_int(hexa_len(chars));
    HexaVal paren_depth = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal ch = hexa_index_get(chars, pos);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ch, hexa_str(" "))) || hexa_truthy(hexa_eq(ch, hexa_str("\t"))))) || hexa_truthy(hexa_eq(ch, hexa_str("\r")))))) {
            pos = hexa_add(pos, hexa_int(1));
            col = hexa_add(col, hexa_int(1));
        } else {
            if (hexa_truthy(hexa_eq(ch, hexa_str("\n")))) {
                if (hexa_truthy(hexa_eq(paren_depth, hexa_int(0)))) {
                    tokens = hexa_array_push(tokens, Token(hexa_str("Newline"), hexa_str("\n"), line, col));
                }
                pos = hexa_add(pos, hexa_int(1));
                line = hexa_add(line, hexa_int(1));
                col = hexa_int(1);
            } else {
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ch, hexa_str("/"))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("/")))))) {
                    pos = hexa_add(pos, hexa_int(2));
                    col = hexa_add(col, hexa_int(2));
                    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("\n")))))))) {
                        pos = hexa_add(pos, hexa_int(1));
                        col = hexa_add(col, hexa_int(1));
                    }
                } else {
                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ch, hexa_str("/"))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("*")))))) {
                        pos = hexa_add(pos, hexa_int(2));
                        col = hexa_add(col, hexa_int(2));
                        HexaVal depth = hexa_int(1);
                        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(depth); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); }))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))))) {
                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("/"))))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("*")))))) {
                                depth = hexa_add(depth, hexa_int(1));
                                pos = hexa_add(pos, hexa_int(2));
                                col = hexa_add(col, hexa_int(2));
                            } else {
                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("*"))))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("/")))))) {
                                    depth = hexa_sub(depth, hexa_int(1));
                                    pos = hexa_add(pos, hexa_int(2));
                                    col = hexa_add(col, hexa_int(2));
                                } else {
                                    if (hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("\n")))) {
                                        pos = hexa_add(pos, hexa_int(1));
                                        line = hexa_add(line, hexa_int(1));
                                        col = hexa_int(1);
                                    } else {
                                        pos = hexa_add(pos, hexa_int(1));
                                        col = hexa_add(col, hexa_int(1));
                                    }
                                }
                            }
                        }
                    } else {
                        if (hexa_truthy(is_ident_start(ch))) {
                            start_col = col;
                            HexaVal word_parts = hexa_array_new();
                            while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(is_ident_char(hexa_index_get(chars, pos)))))) {
                                word_parts = hexa_array_push(word_parts, hexa_to_string(hexa_index_get(chars, pos)));
                                pos = hexa_add(pos, hexa_int(1));
                                col = hexa_add(col, hexa_int(1));
                            }
                            HexaVal word = hexa_str_join(word_parts, hexa_str(""));
                            HexaVal kind = keyword_kind(word);
                            tokens = hexa_array_push(tokens, Token(kind, word, line, start_col));
                        } else {
                            if (hexa_truthy(hexa_bool((ch.tag==TAG_STR && ch.s && isdigit((unsigned char)ch.s[0])) || (ch.tag==TAG_CHAR && isdigit((unsigned char)ch.i))))) {
                                start_col = col;
                                HexaVal num_parts = hexa_array_new();
                                HexaVal is_float = hexa_bool(0);
                                HexaVal is_hex = hexa_bool(0);
                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ch, hexa_str("0"))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))))) && hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("x"))) || hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("X")))))))) {
                                    is_hex = hexa_bool(1);
                                    num_parts = hexa_array_push(num_parts, hexa_str("0x"));
                                    pos = hexa_add(pos, hexa_int(2));
                                    col = hexa_add(col, hexa_int(2));
                                    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(is_hex_digit(hexa_index_get(chars, pos)))))) {
                                        num_parts = hexa_array_push(num_parts, hexa_to_string(hexa_index_get(chars, pos)));
                                        pos = hexa_add(pos, hexa_int(1));
                                        col = hexa_add(col, hexa_int(1));
                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("_")))))) {
                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(is_hex_digit(hexa_index_get(chars, hexa_add(pos, hexa_int(1)))))))) {
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                            }
                                        }
                                    }
                                } else {
                                    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool((hexa_index_get(chars, pos).tag==TAG_STR && hexa_index_get(chars, pos).s && isdigit((unsigned char)hexa_index_get(chars, pos).s[0])) || (hexa_index_get(chars, pos).tag==TAG_CHAR && isdigit((unsigned char)hexa_index_get(chars, pos).i))))))) {
                                        num_parts = hexa_array_push(num_parts, hexa_to_string(hexa_index_get(chars, pos)));
                                        pos = hexa_add(pos, hexa_int(1));
                                        col = hexa_add(col, hexa_int(1));
                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("_")))))) {
                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool((hexa_index_get(chars, hexa_add(pos, hexa_int(1))).tag==TAG_STR && hexa_index_get(chars, hexa_add(pos, hexa_int(1))).s && isdigit((unsigned char)hexa_index_get(chars, hexa_add(pos, hexa_int(1))).s[0])) || (hexa_index_get(chars, hexa_add(pos, hexa_int(1))).tag==TAG_CHAR && isdigit((unsigned char)hexa_index_get(chars, hexa_add(pos, hexa_int(1))).i))))))) {
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                            }
                                        }
                                    }
                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str(".")))))) {
                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool((hexa_index_get(chars, hexa_add(pos, hexa_int(1))).tag==TAG_STR && hexa_index_get(chars, hexa_add(pos, hexa_int(1))).s && isdigit((unsigned char)hexa_index_get(chars, hexa_add(pos, hexa_int(1))).s[0])) || (hexa_index_get(chars, hexa_add(pos, hexa_int(1))).tag==TAG_CHAR && isdigit((unsigned char)hexa_index_get(chars, hexa_add(pos, hexa_int(1))).i))))))) {
                                            is_float = hexa_bool(1);
                                            num_parts = hexa_array_push(num_parts, hexa_str("."));
                                            pos = hexa_add(pos, hexa_int(1));
                                            col = hexa_add(col, hexa_int(1));
                                            while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool((hexa_index_get(chars, pos).tag==TAG_STR && hexa_index_get(chars, pos).s && isdigit((unsigned char)hexa_index_get(chars, pos).s[0])) || (hexa_index_get(chars, pos).tag==TAG_CHAR && isdigit((unsigned char)hexa_index_get(chars, pos).i))))))) {
                                                num_parts = hexa_array_push(num_parts, hexa_to_string(hexa_index_get(chars, pos)));
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("_")))))) {
                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool((hexa_index_get(chars, hexa_add(pos, hexa_int(1))).tag==TAG_STR && hexa_index_get(chars, hexa_add(pos, hexa_int(1))).s && isdigit((unsigned char)hexa_index_get(chars, hexa_add(pos, hexa_int(1))).s[0])) || (hexa_index_get(chars, hexa_add(pos, hexa_int(1))).tag==TAG_CHAR && isdigit((unsigned char)hexa_index_get(chars, hexa_add(pos, hexa_int(1))).i))))))) {
                                                        pos = hexa_add(pos, hexa_int(1));
                                                        col = hexa_add(col, hexa_int(1));
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("e"))) || hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("E")))))))) {
                                        HexaVal ep = hexa_add(pos, hexa_int(1));
                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ep); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_index_get(chars, ep), hexa_str("+"))) || hexa_truthy(hexa_eq(hexa_index_get(chars, ep), hexa_str("-")))))))) {
                                            ep = hexa_add(ep, hexa_int(1));
                                        }
                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ep); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool((hexa_index_get(chars, ep).tag==TAG_STR && hexa_index_get(chars, ep).s && isdigit((unsigned char)hexa_index_get(chars, ep).s[0])) || (hexa_index_get(chars, ep).tag==TAG_CHAR && isdigit((unsigned char)hexa_index_get(chars, ep).i))))))) {
                                            is_float = hexa_bool(1);
                                            num_parts = hexa_array_push(num_parts, hexa_to_string(hexa_index_get(chars, pos)));
                                            pos = hexa_add(pos, hexa_int(1));
                                            col = hexa_add(col, hexa_int(1));
                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("+"))) || hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("-")))))))) {
                                                num_parts = hexa_array_push(num_parts, hexa_to_string(hexa_index_get(chars, pos)));
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                            }
                                            while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool((hexa_index_get(chars, pos).tag==TAG_STR && hexa_index_get(chars, pos).s && isdigit((unsigned char)hexa_index_get(chars, pos).s[0])) || (hexa_index_get(chars, pos).tag==TAG_CHAR && isdigit((unsigned char)hexa_index_get(chars, pos).i))))))) {
                                                num_parts = hexa_array_push(num_parts, hexa_to_string(hexa_index_get(chars, pos)));
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                            }
                                        }
                                    }
                                }
                                HexaVal num_str = hexa_str_join(num_parts, hexa_str(""));
                                if (hexa_truthy(is_float)) {
                                    tokens = hexa_array_push(tokens, Token(hexa_str("FloatLit"), num_str, line, start_col));
                                } else {
                                    tokens = hexa_array_push(tokens, Token(hexa_str("IntLit"), num_str, line, start_col));
                                }
                            } else {
                                if (hexa_truthy(hexa_eq(ch, hexa_str("\"")))) {
                                    start_col = col;
                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(2))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("\""))))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(2))), hexa_str("\"")))))) {
                                        pos = hexa_add(pos, hexa_int(3));
                                        col = hexa_add(col, hexa_int(3));
                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("\n")))))) {
                                            pos = hexa_add(pos, hexa_int(1));
                                            line = hexa_add(line, hexa_int(1));
                                            col = hexa_int(1);
                                        } else {
                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("\r"))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("\n")))))) {
                                                pos = hexa_add(pos, hexa_int(2));
                                                line = hexa_add(line, hexa_int(1));
                                                col = hexa_int(1);
                                            }
                                        }
                                        HexaVal ts_parts = hexa_array_new();
                                        HexaVal ts_done = hexa_bool(0);
                                        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool(!hexa_truthy(ts_done)))))) {
                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(2))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("\""))))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("\""))))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(2))), hexa_str("\"")))))) {
                                                ts_done = hexa_bool(1);
                                                pos = hexa_add(pos, hexa_int(3));
                                                col = hexa_add(col, hexa_int(3));
                                            } else {
                                                HexaVal tc = hexa_index_get(chars, pos);
                                                ts_parts = hexa_array_push(ts_parts, hexa_to_string(tc));
                                                pos = hexa_add(pos, hexa_int(1));
                                                if (hexa_truthy(hexa_eq(tc, hexa_str("\n")))) {
                                                    line = hexa_add(line, hexa_int(1));
                                                    col = hexa_int(1);
                                                } else {
                                                    col = hexa_add(col, hexa_int(1));
                                                }
                                            }
                                        }
                                        HexaVal ts = hexa_str_join(ts_parts, hexa_str(""));
                                        tokens = hexa_array_push(tokens, Token(hexa_str("StringLit"), ts, line, start_col));
                                    } else {
                                        pos = hexa_add(pos, hexa_int(1));
                                        col = hexa_add(col, hexa_int(1));
                                        HexaVal s_parts = hexa_array_new();
                                        HexaVal done = hexa_bool(0);
                                        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool(!hexa_truthy(done)))))) {
                                            HexaVal c = hexa_index_get(chars, pos);
                                            if (hexa_truthy(hexa_eq(c, hexa_str("\"")))) {
                                                done = hexa_bool(1);
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                            } else {
                                                if (hexa_truthy(hexa_eq(c, hexa_str("\\")))) {
                                                    pos = hexa_add(pos, hexa_int(1));
                                                    col = hexa_add(col, hexa_int(1));
                                                    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                                                        esc = hexa_index_get(chars, pos);
                                                        if (hexa_truthy(hexa_eq(esc, hexa_str("n")))) {
                                                            s_parts = hexa_array_push(s_parts, hexa_str("\n"));
                                                        } else {
                                                            if (hexa_truthy(hexa_eq(esc, hexa_str("t")))) {
                                                                s_parts = hexa_array_push(s_parts, hexa_str("\t"));
                                                            } else {
                                                                if (hexa_truthy(hexa_eq(esc, hexa_str("r")))) {
                                                                    s_parts = hexa_array_push(s_parts, hexa_str("\r"));
                                                                } else {
                                                                    if (hexa_truthy(hexa_eq(esc, hexa_str("\\")))) {
                                                                        s_parts = hexa_array_push(s_parts, hexa_str("\\"));
                                                                    } else {
                                                                        if (hexa_truthy(hexa_eq(esc, hexa_str("\"")))) {
                                                                            s_parts = hexa_array_push(s_parts, hexa_str("\""));
                                                                        } else {
                                                                            if (hexa_truthy(hexa_eq(esc, hexa_str("0")))) {
                                                                                s_parts = hexa_array_push(s_parts, hexa_str(""));
                                                                            } else {
                                                                                s_parts = hexa_array_push(s_parts, hexa_to_string(esc));
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                        pos = hexa_add(pos, hexa_int(1));
                                                        col = hexa_add(col, hexa_int(1));
                                                    }
                                                } else {
                                                    s_parts = hexa_array_push(s_parts, hexa_to_string(c));
                                                    pos = hexa_add(pos, hexa_int(1));
                                                    if (hexa_truthy(hexa_eq(c, hexa_str("\n")))) {
                                                        line = hexa_add(line, hexa_int(1));
                                                        col = hexa_int(1);
                                                    } else {
                                                        col = hexa_add(col, hexa_int(1));
                                                    }
                                                }
                                            }
                                        }
                                        HexaVal s = hexa_str_join(s_parts, hexa_str(""));
                                        tokens = hexa_array_push(tokens, Token(hexa_str("StringLit"), s, line, start_col));
                                    }
                                } else {
                                    if (hexa_truthy(hexa_eq(ch, hexa_str("'")))) {
                                        start_col = col;
                                        HexaVal is_label = hexa_bool(0);
                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(is_ident_start(hexa_index_get(chars, hexa_add(pos, hexa_int(1)))))))) {
                                            HexaVal peek_pos = hexa_add(pos, hexa_int(1));
                                            while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(peek_pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(is_ident_char(hexa_index_get(chars, peek_pos)))))) {
                                                peek_pos = hexa_add(peek_pos, hexa_int(1));
                                            }
                                            HexaVal ident_len = hexa_sub(hexa_sub(peek_pos, pos), hexa_int(1));
                                            if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ident_len); HexaVal __r=(hexa_int(1)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                                                is_label = hexa_bool(1);
                                            } else {
                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(peek_pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_index_get(chars, peek_pos), hexa_str("'")))))))) {
                                                    is_label = hexa_bool(1);
                                                }
                                            }
                                        }
                                        if (hexa_truthy(is_label)) {
                                            pos = hexa_add(pos, hexa_int(1));
                                            col = hexa_add(col, hexa_int(1));
                                            HexaVal label_parts = hexa_array_new();
                                            while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(is_ident_char(hexa_index_get(chars, pos)))))) {
                                                label_parts = hexa_array_push(label_parts, hexa_to_string(hexa_index_get(chars, pos)));
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                            }
                                            HexaVal label_name = hexa_str_join(label_parts, hexa_str(""));
                                            tokens = hexa_array_push(tokens, Token(hexa_str("Label"), label_name, line, start_col));
                                        } else {
                                            pos = hexa_add(pos, hexa_int(1));
                                            col = hexa_add(col, hexa_int(1));
                                            HexaVal ch_val = hexa_str("");
                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("\\")))))) {
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                                                    esc = hexa_index_get(chars, pos);
                                                    if (hexa_truthy(hexa_eq(esc, hexa_str("n")))) {
                                                        ch_val = hexa_str("\n");
                                                    } else {
                                                        if (hexa_truthy(hexa_eq(esc, hexa_str("t")))) {
                                                            ch_val = hexa_str("\t");
                                                        } else {
                                                            if (hexa_truthy(hexa_eq(esc, hexa_str("r")))) {
                                                                ch_val = hexa_str("\r");
                                                            } else {
                                                                if (hexa_truthy(hexa_eq(esc, hexa_str("\\")))) {
                                                                    ch_val = hexa_str("\\");
                                                                } else {
                                                                    if (hexa_truthy(hexa_eq(esc, hexa_str("'")))) {
                                                                        ch_val = hexa_str("'");
                                                                    } else {
                                                                        if (hexa_truthy(hexa_eq(esc, hexa_str("0")))) {
                                                                            ch_val = hexa_str("");
                                                                        } else {
                                                                            ch_val = hexa_to_string(esc);
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                    pos = hexa_add(pos, hexa_int(1));
                                                    col = hexa_add(col, hexa_int(1));
                                                }
                                            } else {
                                                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                                                    ch_val = hexa_to_string(hexa_index_get(chars, pos));
                                                    pos = hexa_add(pos, hexa_int(1));
                                                    col = hexa_add(col, hexa_int(1));
                                                }
                                            }
                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, pos), hexa_str("'")))))) {
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                            }
                                            tokens = hexa_array_push(tokens, Token(hexa_str("CharLit"), ch_val, line, start_col));
                                        }
                                    } else {
                                        start_col = col;
                                        if (hexa_truthy(hexa_eq(ch, hexa_str("+")))) {
                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                tokens = hexa_array_push(tokens, Token(hexa_str("PlusEq"), hexa_str("+="), line, start_col));
                                                pos = hexa_add(pos, hexa_int(2));
                                                col = hexa_add(col, hexa_int(2));
                                            } else {
                                                tokens = hexa_array_push(tokens, Token(hexa_str("Plus"), hexa_str("+"), line, start_col));
                                                pos = hexa_add(pos, hexa_int(1));
                                                col = hexa_add(col, hexa_int(1));
                                            }
                                        } else {
                                            if (hexa_truthy(hexa_eq(ch, hexa_str("-")))) {
                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str(">")))))) {
                                                    tokens = hexa_array_push(tokens, Token(hexa_str("Arrow"), hexa_str("->"), line, start_col));
                                                    pos = hexa_add(pos, hexa_int(2));
                                                    col = hexa_add(col, hexa_int(2));
                                                } else {
                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                        tokens = hexa_array_push(tokens, Token(hexa_str("MinusEq"), hexa_str("-="), line, start_col));
                                                        pos = hexa_add(pos, hexa_int(2));
                                                        col = hexa_add(col, hexa_int(2));
                                                    } else {
                                                        tokens = hexa_array_push(tokens, Token(hexa_str("Minus"), hexa_str("-"), line, start_col));
                                                        pos = hexa_add(pos, hexa_int(1));
                                                        col = hexa_add(col, hexa_int(1));
                                                    }
                                                }
                                            } else {
                                                if (hexa_truthy(hexa_eq(ch, hexa_str("*")))) {
                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("*")))))) {
                                                        tokens = hexa_array_push(tokens, Token(hexa_str("Power"), hexa_str("**"), line, start_col));
                                                        pos = hexa_add(pos, hexa_int(2));
                                                        col = hexa_add(col, hexa_int(2));
                                                    } else {
                                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                            tokens = hexa_array_push(tokens, Token(hexa_str("StarEq"), hexa_str("*="), line, start_col));
                                                            pos = hexa_add(pos, hexa_int(2));
                                                            col = hexa_add(col, hexa_int(2));
                                                        } else {
                                                            tokens = hexa_array_push(tokens, Token(hexa_str("Star"), hexa_str("*"), line, start_col));
                                                            pos = hexa_add(pos, hexa_int(1));
                                                            col = hexa_add(col, hexa_int(1));
                                                        }
                                                    }
                                                } else {
                                                    if (hexa_truthy(hexa_eq(ch, hexa_str("/")))) {
                                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                            tokens = hexa_array_push(tokens, Token(hexa_str("SlashEq"), hexa_str("/="), line, start_col));
                                                            pos = hexa_add(pos, hexa_int(2));
                                                            col = hexa_add(col, hexa_int(2));
                                                        } else {
                                                            tokens = hexa_array_push(tokens, Token(hexa_str("Slash"), hexa_str("/"), line, start_col));
                                                            pos = hexa_add(pos, hexa_int(1));
                                                            col = hexa_add(col, hexa_int(1));
                                                        }
                                                    } else {
                                                        if (hexa_truthy(hexa_eq(ch, hexa_str("%")))) {
                                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                                tokens = hexa_array_push(tokens, Token(hexa_str("PercentEq"), hexa_str("%="), line, start_col));
                                                                pos = hexa_add(pos, hexa_int(2));
                                                                col = hexa_add(col, hexa_int(2));
                                                            } else {
                                                                tokens = hexa_array_push(tokens, Token(hexa_str("Percent"), hexa_str("%"), line, start_col));
                                                                pos = hexa_add(pos, hexa_int(1));
                                                                col = hexa_add(col, hexa_int(1));
                                                            }
                                                        } else {
                                                            if (hexa_truthy(hexa_eq(ch, hexa_str("=")))) {
                                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("EqEq"), hexa_str("=="), line, start_col));
                                                                    pos = hexa_add(pos, hexa_int(2));
                                                                    col = hexa_add(col, hexa_int(2));
                                                                } else {
                                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str(">")))))) {
                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("FatArrow"), hexa_str("=>"), line, start_col));
                                                                        pos = hexa_add(pos, hexa_int(2));
                                                                        col = hexa_add(col, hexa_int(2));
                                                                    } else {
                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("Eq"), hexa_str("="), line, start_col));
                                                                        pos = hexa_add(pos, hexa_int(1));
                                                                        col = hexa_add(col, hexa_int(1));
                                                                    }
                                                                }
                                                            } else {
                                                                if (hexa_truthy(hexa_eq(ch, hexa_str("!")))) {
                                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("NotEq"), hexa_str("!="), line, start_col));
                                                                        pos = hexa_add(pos, hexa_int(2));
                                                                        col = hexa_add(col, hexa_int(2));
                                                                    } else {
                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("Not"), hexa_str("!"), line, start_col));
                                                                        pos = hexa_add(pos, hexa_int(1));
                                                                        col = hexa_add(col, hexa_int(1));
                                                                    }
                                                                } else {
                                                                    if (hexa_truthy(hexa_eq(ch, hexa_str("<")))) {
                                                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("LtEq"), hexa_str("<="), line, start_col));
                                                                            pos = hexa_add(pos, hexa_int(2));
                                                                            col = hexa_add(col, hexa_int(2));
                                                                        } else {
                                                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("<")))))) {
                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("Shl"), hexa_str("<<"), line, start_col));
                                                                                pos = hexa_add(pos, hexa_int(2));
                                                                                col = hexa_add(col, hexa_int(2));
                                                                            } else {
                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("Lt"), hexa_str("<"), line, start_col));
                                                                                pos = hexa_add(pos, hexa_int(1));
                                                                                col = hexa_add(col, hexa_int(1));
                                                                            }
                                                                        }
                                                                    } else {
                                                                        if (hexa_truthy(hexa_eq(ch, hexa_str(">")))) {
                                                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("GtEq"), hexa_str(">="), line, start_col));
                                                                                pos = hexa_add(pos, hexa_int(2));
                                                                                col = hexa_add(col, hexa_int(2));
                                                                            } else {
                                                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str(">")))))) {
                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("Shr"), hexa_str(">>"), line, start_col));
                                                                                    pos = hexa_add(pos, hexa_int(2));
                                                                                    col = hexa_add(col, hexa_int(2));
                                                                                } else {
                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("Gt"), hexa_str(">"), line, start_col));
                                                                                    pos = hexa_add(pos, hexa_int(1));
                                                                                    col = hexa_add(col, hexa_int(1));
                                                                                }
                                                                            }
                                                                        } else {
                                                                            if (hexa_truthy(hexa_eq(ch, hexa_str("&")))) {
                                                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("&")))))) {
                                                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(2))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(2))), hexa_str("=")))))) {
                                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("AndAssign"), hexa_str("&&="), line, start_col));
                                                                                        pos = hexa_add(pos, hexa_int(3));
                                                                                        col = hexa_add(col, hexa_int(3));
                                                                                    } else {
                                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("And"), hexa_str("&&"), line, start_col));
                                                                                        pos = hexa_add(pos, hexa_int(2));
                                                                                        col = hexa_add(col, hexa_int(2));
                                                                                    }
                                                                                } else {
                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("BitAnd"), hexa_str("&"), line, start_col));
                                                                                    pos = hexa_add(pos, hexa_int(1));
                                                                                    col = hexa_add(col, hexa_int(1));
                                                                                }
                                                                            } else {
                                                                                if (hexa_truthy(hexa_eq(ch, hexa_str("|")))) {
                                                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("|")))))) {
                                                                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(2))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(2))), hexa_str("=")))))) {
                                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("OrAssign"), hexa_str("||="), line, start_col));
                                                                                            pos = hexa_add(pos, hexa_int(3));
                                                                                            col = hexa_add(col, hexa_int(3));
                                                                                        } else {
                                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("Or"), hexa_str("||"), line, start_col));
                                                                                            pos = hexa_add(pos, hexa_int(2));
                                                                                            col = hexa_add(col, hexa_int(2));
                                                                                        }
                                                                                    } else {
                                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("BitOr"), hexa_str("|"), line, start_col));
                                                                                        pos = hexa_add(pos, hexa_int(1));
                                                                                        col = hexa_add(col, hexa_int(1));
                                                                                    }
                                                                                } else {
                                                                                    if (hexa_truthy(hexa_eq(ch, hexa_str("^")))) {
                                                                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("^")))))) {
                                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("Xor"), hexa_str("^^"), line, start_col));
                                                                                            pos = hexa_add(pos, hexa_int(2));
                                                                                            col = hexa_add(col, hexa_int(2));
                                                                                        } else {
                                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("BitXor"), hexa_str("^"), line, start_col));
                                                                                            pos = hexa_add(pos, hexa_int(1));
                                                                                            col = hexa_add(col, hexa_int(1));
                                                                                        }
                                                                                    } else {
                                                                                        if (hexa_truthy(hexa_eq(ch, hexa_str("~")))) {
                                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("BitNot"), hexa_str("~"), line, start_col));
                                                                                            pos = hexa_add(pos, hexa_int(1));
                                                                                            col = hexa_add(col, hexa_int(1));
                                                                                        } else {
                                                                                            if (hexa_truthy(hexa_eq(ch, hexa_str("?")))) {
                                                                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("?")))))) {
                                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("NullCoal"), hexa_str("??"), line, start_col));
                                                                                                    pos = hexa_add(pos, hexa_int(2));
                                                                                                    col = hexa_add(col, hexa_int(2));
                                                                                                } else {
                                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("Question"), hexa_str("?"), line, start_col));
                                                                                                    pos = hexa_add(pos, hexa_int(1));
                                                                                                    col = hexa_add(col, hexa_int(1));
                                                                                                }
                                                                                            } else {
                                                                                                if (hexa_truthy(hexa_eq(ch, hexa_str("@")))) {
                                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("At"), hexa_str("@"), line, start_col));
                                                                                                    pos = hexa_add(pos, hexa_int(1));
                                                                                                    col = hexa_add(col, hexa_int(1));
                                                                                                } else {
                                                                                                    if (hexa_truthy(hexa_eq(ch, hexa_str(":")))) {
                                                                                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("=")))))) {
                                                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("ColonEq"), hexa_str(":="), line, start_col));
                                                                                                            pos = hexa_add(pos, hexa_int(2));
                                                                                                            col = hexa_add(col, hexa_int(2));
                                                                                                        } else {
                                                                                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str(":")))))) {
                                                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("ColonColon"), hexa_str("::"), line, start_col));
                                                                                                                pos = hexa_add(pos, hexa_int(2));
                                                                                                                col = hexa_add(col, hexa_int(2));
                                                                                                            } else {
                                                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("Colon"), hexa_str(":"), line, start_col));
                                                                                                                pos = hexa_add(pos, hexa_int(1));
                                                                                                                col = hexa_add(col, hexa_int(1));
                                                                                                            }
                                                                                                        }
                                                                                                    } else {
                                                                                                        if (hexa_truthy(hexa_eq(ch, hexa_str(".")))) {
                                                                                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(2))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("."))))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(2))), hexa_str(".")))))) {
                                                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("DotDotDot"), hexa_str("..."), line, start_col));
                                                                                                                pos = hexa_add(pos, hexa_int(3));
                                                                                                                col = hexa_add(col, hexa_int(3));
                                                                                                            } else {
                                                                                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str(".")))))) {
                                                                                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(2))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(2))), hexa_str("=")))))) {
                                                                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("DotDotEq"), hexa_str("..="), line, start_col));
                                                                                                                        pos = hexa_add(pos, hexa_int(3));
                                                                                                                        col = hexa_add(col, hexa_int(3));
                                                                                                                    } else {
                                                                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("DotDot"), hexa_str(".."), line, start_col));
                                                                                                                        pos = hexa_add(pos, hexa_int(2));
                                                                                                                        col = hexa_add(col, hexa_int(2));
                                                                                                                    }
                                                                                                                } else {
                                                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("Dot"), hexa_str("."), line, start_col));
                                                                                                                    pos = hexa_add(pos, hexa_int(1));
                                                                                                                    col = hexa_add(col, hexa_int(1));
                                                                                                                }
                                                                                                            }
                                                                                                        } else {
                                                                                                            if (hexa_truthy(hexa_eq(ch, hexa_str("(")))) {
                                                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("LParen"), hexa_str("("), line, start_col));
                                                                                                                paren_depth = hexa_add(paren_depth, hexa_int(1));
                                                                                                                pos = hexa_add(pos, hexa_int(1));
                                                                                                                col = hexa_add(col, hexa_int(1));
                                                                                                            } else {
                                                                                                                if (hexa_truthy(hexa_eq(ch, hexa_str(")")))) {
                                                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("RParen"), hexa_str(")"), line, start_col));
                                                                                                                    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(paren_depth); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                                                                                                                        paren_depth = hexa_sub(paren_depth, hexa_int(1));
                                                                                                                    }
                                                                                                                    pos = hexa_add(pos, hexa_int(1));
                                                                                                                    col = hexa_add(col, hexa_int(1));
                                                                                                                } else {
                                                                                                                    if (hexa_truthy(hexa_eq(ch, hexa_str("{")))) {
                                                                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("LBrace"), hexa_str("{"), line, start_col));
                                                                                                                        pos = hexa_add(pos, hexa_int(1));
                                                                                                                        col = hexa_add(col, hexa_int(1));
                                                                                                                    } else {
                                                                                                                        if (hexa_truthy(hexa_eq(ch, hexa_str("}")))) {
                                                                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("RBrace"), hexa_str("}"), line, start_col));
                                                                                                                            pos = hexa_add(pos, hexa_int(1));
                                                                                                                            col = hexa_add(col, hexa_int(1));
                                                                                                                        } else {
                                                                                                                            if (hexa_truthy(hexa_eq(ch, hexa_str("[")))) {
                                                                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("LBracket"), hexa_str("["), line, start_col));
                                                                                                                                paren_depth = hexa_add(paren_depth, hexa_int(1));
                                                                                                                                pos = hexa_add(pos, hexa_int(1));
                                                                                                                                col = hexa_add(col, hexa_int(1));
                                                                                                                            } else {
                                                                                                                                if (hexa_truthy(hexa_eq(ch, hexa_str("]")))) {
                                                                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("RBracket"), hexa_str("]"), line, start_col));
                                                                                                                                    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(paren_depth); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                                                                                                                                        paren_depth = hexa_sub(paren_depth, hexa_int(1));
                                                                                                                                    }
                                                                                                                                    pos = hexa_add(pos, hexa_int(1));
                                                                                                                                    col = hexa_add(col, hexa_int(1));
                                                                                                                                } else {
                                                                                                                                    if (hexa_truthy(hexa_eq(ch, hexa_str(",")))) {
                                                                                                                                        tokens = hexa_array_push(tokens, Token(hexa_str("Comma"), hexa_str(","), line, start_col));
                                                                                                                                        pos = hexa_add(pos, hexa_int(1));
                                                                                                                                        col = hexa_add(col, hexa_int(1));
                                                                                                                                    } else {
                                                                                                                                        if (hexa_truthy(hexa_eq(ch, hexa_str(";")))) {
                                                                                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("Semicolon"), hexa_str(";"), line, start_col));
                                                                                                                                            pos = hexa_add(pos, hexa_int(1));
                                                                                                                                            col = hexa_add(col, hexa_int(1));
                                                                                                                                        } else {
                                                                                                                                            if (hexa_truthy(hexa_eq(ch, hexa_str("?")))) {
                                                                                                                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str(".")))))) {
                                                                                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("QuestionDot"), hexa_str("?."), line, start_col));
                                                                                                                                                    pos = hexa_add(pos, hexa_int(2));
                                                                                                                                                    col = hexa_add(col, hexa_int(2));
                                                                                                                                                } else {
                                                                                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("Question"), hexa_str("?"), line, start_col));
                                                                                                                                                    pos = hexa_add(pos, hexa_int(1));
                                                                                                                                                    col = hexa_add(col, hexa_int(1));
                                                                                                                                                }
                                                                                                                                            } else {
                                                                                                                                                if (hexa_truthy(hexa_eq(ch, hexa_str("@")))) {
                                                                                                                                                    pos = hexa_add(pos, hexa_int(1));
                                                                                                                                                    col = hexa_add(col, hexa_int(1));
                                                                                                                                                    HexaVal attr_parts = hexa_array_new();
                                                                                                                                                    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pos); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(is_ident_char(hexa_index_get(chars, pos)))))) {
                                                                                                                                                        attr_parts = hexa_array_push(attr_parts, hexa_to_string(hexa_index_get(chars, pos)));
                                                                                                                                                        pos = hexa_add(pos, hexa_int(1));
                                                                                                                                                        col = hexa_add(col, hexa_int(1));
                                                                                                                                                    }
                                                                                                                                                    HexaVal attr_name = hexa_str_join(attr_parts, hexa_str(""));
                                                                                                                                                    tokens = hexa_array_push(tokens, Token(hexa_str("Attribute"), attr_name, line, start_col));
                                                                                                                                                } else {
                                                                                                                                                    if (hexa_truthy(hexa_eq(ch, hexa_str("?")))) {
                                                                                                                                                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("?")))))) {
                                                                                                                                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(2))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(2))), hexa_str("=")))))) {
                                                                                                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("NullCoalescingAssign"), hexa_str("??="), line, start_col));
                                                                                                                                                                pos = hexa_add(pos, hexa_int(3));
                                                                                                                                                                col = hexa_add(col, hexa_int(3));
                                                                                                                                                            } else {
                                                                                                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("NullCoalescing"), hexa_str("??"), line, start_col));
                                                                                                                                                                pos = hexa_add(pos, hexa_int(2));
                                                                                                                                                                col = hexa_add(col, hexa_int(2));
                                                                                                                                                            }
                                                                                                                                                        } else {
                                                                                                                                                            tokens = hexa_array_push(tokens, Token(hexa_str("Question"), hexa_str("?"), line, start_col));
                                                                                                                                                            pos = hexa_add(pos, hexa_int(1));
                                                                                                                                                            col = hexa_add(col, hexa_int(1));
                                                                                                                                                        }
                                                                                                                                                    } else {
                                                                                                                                                        if (hexa_truthy(hexa_eq(ch, hexa_str("#")))) {
                                                                                                                                                            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_add(pos, hexa_int(1))); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_eq(hexa_index_get(chars, hexa_add(pos, hexa_int(1))), hexa_str("{")))))) {
                                                                                                                                                                tokens = hexa_array_push(tokens, Token(hexa_str("HashLBrace"), hexa_str("#{"), line, start_col));
                                                                                                                                                                pos = hexa_add(pos, hexa_int(2));
                                                                                                                                                                col = hexa_add(col, hexa_int(2));
                                                                                                                                                            } else {
                                                                                                                                                                pos = hexa_add(pos, hexa_int(1));
                                                                                                                                                                col = hexa_add(col, hexa_int(1));
                                                                                                                                                            }
                                                                                                                                                        } else {
                                                                                                                                                            pos = hexa_add(pos, hexa_int(1));
                                                                                                                                                            col = hexa_add(col, hexa_int(1));
                                                                                                                                                        }
                                                                                                                                                    }
                                                                                                                                                }
                                                                                                                                            }
                                                                                                                                        }
                                                                                                                                    }
                                                                                                                                }
                                                                                                                            }
                                                                                                                        }
                                                                                                                    }
                                                                                                                }
                                                                                                            }
                                                                                                        }
                                                                                                    }
                                                                                                }
                                                                                            }
                                                                                        }
                                                                                    }
                                                                                }
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    tokens = hexa_array_push(tokens, Token(hexa_str("Eof"), hexa_str(""), line, col));
    return tokens;
    return hexa_void();
}


HexaVal count_kind(HexaVal tokens, HexaVal kind) {
    HexaVal count = hexa_int(0);
    {
        HexaVal __iter_arr = tokens;
        for (int __fi = 0; __fi < hexa_len(__iter_arr); __fi++) {
            HexaVal t = hexa_iter_get(__iter_arr, __fi);
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(t, "kind", &__hexa_lexer_ic_0), kind))) {
                count = hexa_add(count, hexa_int(1));
            }
        }
    }
    return count;
    return hexa_void();
}


int _lexer_init(int argc, char** argv) {
    hexa_set_args(argc, argv);
    return 0;
}

// === parser ===


HexaVal p_peek(void);
HexaVal p_at_end(void);
HexaVal p_advance(void);
HexaVal parse_stmt(void);
HexaVal parse_let(void);
HexaVal parse_const(void);
HexaVal parse_static(void);
HexaVal parse_return(void);
HexaVal parse_proof_stmt(void);
HexaVal parse_assert_stmt(void);
HexaVal parse_resume_stmt(void);
HexaVal parse_invariant_stmt(void);
HexaVal parse_invariant_decl(void);
HexaVal parse_use_decl(void);
HexaVal parse_mod_decl(void);
HexaVal parse_fn_decl(void);
HexaVal contract_wrap_returns(HexaVal body, HexaVal ens_expr, HexaVal fn_name, HexaVal ens_text);
HexaVal parse_type_annotation(void);
HexaVal parse_params(void);
HexaVal parse_struct_decl(void);
HexaVal parse_enum_decl(void);
HexaVal parse_trait_decl(void);
HexaVal parse_impl_block(void);
HexaVal parse_for_stmt(void);
HexaVal parse_while_stmt(void);
HexaVal parse_loop_stmt(void);
HexaVal parse_match_pattern(void);
HexaVal parse_guard_stmt(void);
HexaVal parse_with_stmt(void);
HexaVal parse_block(void);
HexaVal parse_expr(void);
HexaVal parse_pipe(void);
HexaVal parse_null_coal(void);
HexaVal parse_or(void);
HexaVal parse_and(void);
HexaVal parse_bit_ops(void);
HexaVal parse_comparison(void);
HexaVal parse_bitwise(void);
HexaVal parse_addition(void);
HexaVal parse_multiplication(void);
HexaVal parse_unary(void);
HexaVal parse_postfix(void);
HexaVal parse_args(void);
HexaVal parse_primary(void);
HexaVal parse_try_catch(void);
HexaVal parse_throw_stmt(void);
HexaVal parse_panic_stmt(void);
HexaVal parse_recover_stmt(void);
HexaVal parse_drop_stmt(void);
HexaVal parse_spawn_stmt(void);
HexaVal parse_scope_stmt(void);
HexaVal parse_select_stmt(void);
HexaVal parse_async_fn(void);
HexaVal parse_attribute_prefix(void);
HexaVal parse_extern_fn(void);
HexaVal parse_type_alias(void);
HexaVal parse_atomic_let(void);
HexaVal parse_break_stmt(void);
HexaVal parse_continue_stmt(void);
HexaVal parse_do_while_stmt(void);
HexaVal parse_defer_stmt(void);
HexaVal parse_labeled_loop(void);
HexaVal parse_yield_stmt(void);
HexaVal parse_comptime_stmt(void);
HexaVal parse_intent_stmt(void);
HexaVal parse_verify_stmt(void);
HexaVal parse_generate_stmt(void);
HexaVal parse_optimize_stmt(void);
HexaVal parse_effect_decl(void);
HexaVal parse_pure_fn(void);
HexaVal parse_macro_def(void);
HexaVal parse_derive_decl(void);
HexaVal parse_theorem_stmt(void);
HexaVal parse_handle_stmt(void);
HexaVal parse_visibility(void);
HexaVal parse_type_params(void);

HexaVal p_tokens;
HexaVal p_pos;
HexaVal p_pending_symbol;
HexaVal p_pending_link;
HexaVal p_pending_attrs;
HexaVal p_pending_contract_requires;
HexaVal p_pending_contract_ensures;
HexaVal p_pending_contract_req_text;
HexaVal p_pending_contract_ens_text;
HexaVal p_suppress_struct_lit;
HexaVal p_errors;
HexaVal p_max_errors;
HexaVal p_last_err_key;

static HexaIC __hexa_parser_ic_0 = {0};
static HexaIC __hexa_parser_ic_1 = {0};
static HexaIC __hexa_parser_ic_2 = {0};
static HexaIC __hexa_parser_ic_3 = {0};
static HexaIC __hexa_parser_ic_4 = {0};
static HexaIC __hexa_parser_ic_5 = {0};
static HexaIC __hexa_parser_ic_6 = {0};
static HexaIC __hexa_parser_ic_7 = {0};
static HexaIC __hexa_parser_ic_8 = {0};
static HexaIC __hexa_parser_ic_9 = {0};
static HexaIC __hexa_parser_ic_10 = {0};
static HexaIC __hexa_parser_ic_11 = {0};
static HexaIC __hexa_parser_ic_12 = {0};
static HexaIC __hexa_parser_ic_13 = {0};
static HexaIC __hexa_parser_ic_14 = {0};
static HexaIC __hexa_parser_ic_15 = {0};
static HexaIC __hexa_parser_ic_16 = {0};
static HexaIC __hexa_parser_ic_17 = {0};
static HexaIC __hexa_parser_ic_18 = {0};
static HexaIC __hexa_parser_ic_19 = {0};
static HexaIC __hexa_parser_ic_20 = {0};
static HexaIC __hexa_parser_ic_21 = {0};
static HexaIC __hexa_parser_ic_22 = {0};
static HexaIC __hexa_parser_ic_23 = {0};
static HexaIC __hexa_parser_ic_24 = {0};
static HexaIC __hexa_parser_ic_25 = {0};
static HexaIC __hexa_parser_ic_26 = {0};
static HexaIC __hexa_parser_ic_27 = {0};
static HexaIC __hexa_parser_ic_28 = {0};
static HexaIC __hexa_parser_ic_29 = {0};
static HexaIC __hexa_parser_ic_30 = {0};
static HexaIC __hexa_parser_ic_31 = {0};
static HexaIC __hexa_parser_ic_32 = {0};
static HexaIC __hexa_parser_ic_33 = {0};
static HexaIC __hexa_parser_ic_34 = {0};
static HexaIC __hexa_parser_ic_35 = {0};
static HexaIC __hexa_parser_ic_36 = {0};
static HexaIC __hexa_parser_ic_37 = {0};
static HexaIC __hexa_parser_ic_38 = {0};
static HexaIC __hexa_parser_ic_39 = {0};
static HexaIC __hexa_parser_ic_40 = {0};
static HexaIC __hexa_parser_ic_41 = {0};
static HexaIC __hexa_parser_ic_42 = {0};
static HexaIC __hexa_parser_ic_43 = {0};
static HexaIC __hexa_parser_ic_44 = {0};
static HexaIC __hexa_parser_ic_45 = {0};
static HexaIC __hexa_parser_ic_46 = {0};
static HexaIC __hexa_parser_ic_47 = {0};
static HexaIC __hexa_parser_ic_48 = {0};
static HexaIC __hexa_parser_ic_49 = {0};
static HexaIC __hexa_parser_ic_50 = {0};
static HexaIC __hexa_parser_ic_51 = {0};
static HexaIC __hexa_parser_ic_52 = {0};
static HexaIC __hexa_parser_ic_53 = {0};
static HexaIC __hexa_parser_ic_54 = {0};
static HexaIC __hexa_parser_ic_55 = {0};
static HexaIC __hexa_parser_ic_56 = {0};
static HexaIC __hexa_parser_ic_57 = {0};
static HexaIC __hexa_parser_ic_58 = {0};
static HexaIC __hexa_parser_ic_59 = {0};
static HexaIC __hexa_parser_ic_60 = {0};
static HexaIC __hexa_parser_ic_61 = {0};
static HexaIC __hexa_parser_ic_62 = {0};
static HexaIC __hexa_parser_ic_63 = {0};
static HexaIC __hexa_parser_ic_64 = {0};
static HexaIC __hexa_parser_ic_65 = {0};
static HexaIC __hexa_parser_ic_66 = {0};
static HexaIC __hexa_parser_ic_67 = {0};
static HexaIC __hexa_parser_ic_68 = {0};
static HexaIC __hexa_parser_ic_69 = {0};
static HexaIC __hexa_parser_ic_70 = {0};
static HexaIC __hexa_parser_ic_71 = {0};
static HexaIC __hexa_parser_ic_72 = {0};
static HexaIC __hexa_parser_ic_73 = {0};
static HexaIC __hexa_parser_ic_74 = {0};
static HexaIC __hexa_parser_ic_75 = {0};
static HexaIC __hexa_parser_ic_76 = {0};
static HexaIC __hexa_parser_ic_77 = {0};
static HexaIC __hexa_parser_ic_78 = {0};
static HexaIC __hexa_parser_ic_79 = {0};
static HexaIC __hexa_parser_ic_80 = {0};
static HexaIC __hexa_parser_ic_81 = {0};
static HexaIC __hexa_parser_ic_82 = {0};
static HexaIC __hexa_parser_ic_83 = {0};
static HexaIC __hexa_parser_ic_84 = {0};
static HexaIC __hexa_parser_ic_85 = {0};
static HexaIC __hexa_parser_ic_86 = {0};
static HexaIC __hexa_parser_ic_87 = {0};
static HexaIC __hexa_parser_ic_88 = {0};
static HexaIC __hexa_parser_ic_89 = {0};
static HexaIC __hexa_parser_ic_90 = {0};
static HexaIC __hexa_parser_ic_91 = {0};
static HexaIC __hexa_parser_ic_92 = {0};
static HexaIC __hexa_parser_ic_93 = {0};
static HexaIC __hexa_parser_ic_94 = {0};
static HexaIC __hexa_parser_ic_95 = {0};
static HexaIC __hexa_parser_ic_96 = {0};
static HexaIC __hexa_parser_ic_97 = {0};
static HexaIC __hexa_parser_ic_98 = {0};
static HexaIC __hexa_parser_ic_99 = {0};
static HexaIC __hexa_parser_ic_100 = {0};
static HexaIC __hexa_parser_ic_101 = {0};
static HexaIC __hexa_parser_ic_102 = {0};
static HexaIC __hexa_parser_ic_103 = {0};
static HexaIC __hexa_parser_ic_104 = {0};
static HexaIC __hexa_parser_ic_105 = {0};
static HexaIC __hexa_parser_ic_106 = {0};
static HexaIC __hexa_parser_ic_107 = {0};
static HexaIC __hexa_parser_ic_108 = {0};
static HexaIC __hexa_parser_ic_109 = {0};
static HexaIC __hexa_parser_ic_110 = {0};
static HexaIC __hexa_parser_ic_111 = {0};
static HexaIC __hexa_parser_ic_112 = {0};
static HexaIC __hexa_parser_ic_113 = {0};
static HexaIC __hexa_parser_ic_114 = {0};
static HexaIC __hexa_parser_ic_115 = {0};
static HexaIC __hexa_parser_ic_116 = {0};
static HexaIC __hexa_parser_ic_117 = {0};
static HexaIC __hexa_parser_ic_118 = {0};
static HexaIC __hexa_parser_ic_119 = {0};
static HexaIC __hexa_parser_ic_120 = {0};
static HexaIC __hexa_parser_ic_121 = {0};
static HexaIC __hexa_parser_ic_122 = {0};
static HexaIC __hexa_parser_ic_123 = {0};
static HexaIC __hexa_parser_ic_124 = {0};
static HexaIC __hexa_parser_ic_125 = {0};
static HexaIC __hexa_parser_ic_126 = {0};
static HexaIC __hexa_parser_ic_127 = {0};
static HexaIC __hexa_parser_ic_128 = {0};
static HexaIC __hexa_parser_ic_129 = {0};
static HexaIC __hexa_parser_ic_130 = {0};
static HexaIC __hexa_parser_ic_131 = {0};
static HexaIC __hexa_parser_ic_132 = {0};
static HexaIC __hexa_parser_ic_133 = {0};
static HexaIC __hexa_parser_ic_134 = {0};
static HexaIC __hexa_parser_ic_135 = {0};
static HexaIC __hexa_parser_ic_136 = {0};
static HexaIC __hexa_parser_ic_137 = {0};
static HexaIC __hexa_parser_ic_138 = {0};
static HexaIC __hexa_parser_ic_139 = {0};
static HexaIC __hexa_parser_ic_140 = {0};
static HexaIC __hexa_parser_ic_141 = {0};
static HexaIC __hexa_parser_ic_142 = {0};
static HexaIC __hexa_parser_ic_143 = {0};
static HexaIC __hexa_parser_ic_144 = {0};
static HexaIC __hexa_parser_ic_145 = {0};
static HexaIC __hexa_parser_ic_146 = {0};
static HexaIC __hexa_parser_ic_147 = {0};
static HexaIC __hexa_parser_ic_148 = {0};
static HexaIC __hexa_parser_ic_149 = {0};
static HexaIC __hexa_parser_ic_150 = {0};
static HexaIC __hexa_parser_ic_151 = {0};
static HexaIC __hexa_parser_ic_152 = {0};
static HexaIC __hexa_parser_ic_153 = {0};
static HexaIC __hexa_parser_ic_154 = {0};
static HexaIC __hexa_parser_ic_155 = {0};
static HexaIC __hexa_parser_ic_156 = {0};
static HexaIC __hexa_parser_ic_157 = {0};
static HexaIC __hexa_parser_ic_158 = {0};
static HexaIC __hexa_parser_ic_159 = {0};
static HexaIC __hexa_parser_ic_160 = {0};
static HexaIC __hexa_parser_ic_161 = {0};
static HexaIC __hexa_parser_ic_162 = {0};
static HexaIC __hexa_parser_ic_163 = {0};
static HexaIC __hexa_parser_ic_164 = {0};
static HexaIC __hexa_parser_ic_165 = {0};
static HexaIC __hexa_parser_ic_166 = {0};
static HexaIC __hexa_parser_ic_167 = {0};
static HexaIC __hexa_parser_ic_168 = {0};
static HexaIC __hexa_parser_ic_169 = {0};
static HexaIC __hexa_parser_ic_170 = {0};
static HexaIC __hexa_parser_ic_171 = {0};
static HexaIC __hexa_parser_ic_172 = {0};
static HexaIC __hexa_parser_ic_173 = {0};
static HexaIC __hexa_parser_ic_174 = {0};
static HexaIC __hexa_parser_ic_175 = {0};
static HexaIC __hexa_parser_ic_176 = {0};
static HexaIC __hexa_parser_ic_177 = {0};
static HexaIC __hexa_parser_ic_178 = {0};
static HexaIC __hexa_parser_ic_179 = {0};
static HexaIC __hexa_parser_ic_180 = {0};
static HexaIC __hexa_parser_ic_181 = {0};
static HexaIC __hexa_parser_ic_182 = {0};
static HexaIC __hexa_parser_ic_183 = {0};
static HexaIC __hexa_parser_ic_184 = {0};
static HexaIC __hexa_parser_ic_185 = {0};
static HexaIC __hexa_parser_ic_186 = {0};
static HexaIC __hexa_parser_ic_187 = {0};
static HexaIC __hexa_parser_ic_188 = {0};
static HexaIC __hexa_parser_ic_189 = {0};
static HexaIC __hexa_parser_ic_190 = {0};
static HexaIC __hexa_parser_ic_191 = {0};
static HexaIC __hexa_parser_ic_192 = {0};
static HexaIC __hexa_parser_ic_193 = {0};
static HexaIC __hexa_parser_ic_194 = {0};
static HexaIC __hexa_parser_ic_195 = {0};
static HexaIC __hexa_parser_ic_196 = {0};
static HexaIC __hexa_parser_ic_197 = {0};
static HexaIC __hexa_parser_ic_198 = {0};
static HexaIC __hexa_parser_ic_199 = {0};
static HexaIC __hexa_parser_ic_200 = {0};
static HexaIC __hexa_parser_ic_201 = {0};
static HexaIC __hexa_parser_ic_202 = {0};
static HexaIC __hexa_parser_ic_203 = {0};
static HexaIC __hexa_parser_ic_204 = {0};
static HexaIC __hexa_parser_ic_205 = {0};
static HexaIC __hexa_parser_ic_206 = {0};
static HexaIC __hexa_parser_ic_207 = {0};
static HexaIC __hexa_parser_ic_208 = {0};
static HexaIC __hexa_parser_ic_209 = {0};
static HexaIC __hexa_parser_ic_210 = {0};
static HexaIC __hexa_parser_ic_211 = {0};
static HexaIC __hexa_parser_ic_212 = {0};
static HexaIC __hexa_parser_ic_213 = {0};
static HexaIC __hexa_parser_ic_214 = {0};
static HexaIC __hexa_parser_ic_215 = {0};
static HexaIC __hexa_parser_ic_216 = {0};
static HexaIC __hexa_parser_ic_217 = {0};
static HexaIC __hexa_parser_ic_218 = {0};
static HexaIC __hexa_parser_ic_219 = {0};
static HexaIC __hexa_parser_ic_220 = {0};
static HexaIC __hexa_parser_ic_221 = {0};
static HexaIC __hexa_parser_ic_222 = {0};
static HexaIC __hexa_parser_ic_223 = {0};
static HexaIC __hexa_parser_ic_224 = {0};
static HexaIC __hexa_parser_ic_225 = {0};
static HexaIC __hexa_parser_ic_226 = {0};
static HexaIC __hexa_parser_ic_227 = {0};
static HexaIC __hexa_parser_ic_228 = {0};
static HexaIC __hexa_parser_ic_229 = {0};
static HexaIC __hexa_parser_ic_230 = {0};
static HexaIC __hexa_parser_ic_231 = {0};
static HexaIC __hexa_parser_ic_232 = {0};
static HexaIC __hexa_parser_ic_233 = {0};
static HexaIC __hexa_parser_ic_234 = {0};
static HexaIC __hexa_parser_ic_235 = {0};
static HexaIC __hexa_parser_ic_236 = {0};
static HexaIC __hexa_parser_ic_237 = {0};
static HexaIC __hexa_parser_ic_238 = {0};
static HexaIC __hexa_parser_ic_239 = {0};
static HexaIC __hexa_parser_ic_240 = {0};
static HexaIC __hexa_parser_ic_241 = {0};
static HexaIC __hexa_parser_ic_242 = {0};
static HexaIC __hexa_parser_ic_243 = {0};
static HexaIC __hexa_parser_ic_244 = {0};
static HexaIC __hexa_parser_ic_245 = {0};
static HexaIC __hexa_parser_ic_246 = {0};
static HexaIC __hexa_parser_ic_247 = {0};
static HexaIC __hexa_parser_ic_248 = {0};
static HexaIC __hexa_parser_ic_249 = {0};
static HexaIC __hexa_parser_ic_250 = {0};
static HexaIC __hexa_parser_ic_251 = {0};
static HexaIC __hexa_parser_ic_252 = {0};
static HexaIC __hexa_parser_ic_253 = {0};
static HexaIC __hexa_parser_ic_254 = {0};
static HexaIC __hexa_parser_ic_255 = {0};
static HexaIC __hexa_parser_ic_256 = {0};
static HexaIC __hexa_parser_ic_257 = {0};
static HexaIC __hexa_parser_ic_258 = {0};
static HexaIC __hexa_parser_ic_259 = {0};
static HexaIC __hexa_parser_ic_260 = {0};
static HexaIC __hexa_parser_ic_261 = {0};
static HexaIC __hexa_parser_ic_262 = {0};
static HexaIC __hexa_parser_ic_263 = {0};
static HexaIC __hexa_parser_ic_264 = {0};
static HexaIC __hexa_parser_ic_265 = {0};
static HexaIC __hexa_parser_ic_266 = {0};
static HexaIC __hexa_parser_ic_267 = {0};
static HexaIC __hexa_parser_ic_268 = {0};
static HexaIC __hexa_parser_ic_269 = {0};
static HexaIC __hexa_parser_ic_270 = {0};
static HexaIC __hexa_parser_ic_271 = {0};
static HexaIC __hexa_parser_ic_272 = {0};
static HexaIC __hexa_parser_ic_273 = {0};
static HexaIC __hexa_parser_ic_274 = {0};
static HexaIC __hexa_parser_ic_275 = {0};
static HexaIC __hexa_parser_ic_276 = {0};
static HexaIC __hexa_parser_ic_277 = {0};
static HexaIC __hexa_parser_ic_278 = {0};
static HexaIC __hexa_parser_ic_279 = {0};
static HexaIC __hexa_parser_ic_280 = {0};
static HexaIC __hexa_parser_ic_281 = {0};
static HexaIC __hexa_parser_ic_282 = {0};
static HexaIC __hexa_parser_ic_283 = {0};
static HexaIC __hexa_parser_ic_284 = {0};
static HexaIC __hexa_parser_ic_285 = {0};
static HexaIC __hexa_parser_ic_286 = {0};
static HexaIC __hexa_parser_ic_287 = {0};
static HexaIC __hexa_parser_ic_288 = {0};
static HexaIC __hexa_parser_ic_289 = {0};
static HexaIC __hexa_parser_ic_290 = {0};
static HexaIC __hexa_parser_ic_291 = {0};
static HexaIC __hexa_parser_ic_292 = {0};
static HexaIC __hexa_parser_ic_293 = {0};
static HexaIC __hexa_parser_ic_294 = {0};
static HexaIC __hexa_parser_ic_295 = {0};
static HexaIC __hexa_parser_ic_296 = {0};
static HexaIC __hexa_parser_ic_297 = {0};
static HexaIC __hexa_parser_ic_298 = {0};
static HexaIC __hexa_parser_ic_299 = {0};
static HexaIC __hexa_parser_ic_300 = {0};
static HexaIC __hexa_parser_ic_301 = {0};
static HexaIC __hexa_parser_ic_302 = {0};
static HexaIC __hexa_parser_ic_303 = {0};
static HexaIC __hexa_parser_ic_304 = {0};
static HexaIC __hexa_parser_ic_305 = {0};
static HexaIC __hexa_parser_ic_306 = {0};
static HexaIC __hexa_parser_ic_307 = {0};
static HexaIC __hexa_parser_ic_308 = {0};
static HexaIC __hexa_parser_ic_309 = {0};
static HexaIC __hexa_parser_ic_310 = {0};
static HexaIC __hexa_parser_ic_311 = {0};
static HexaIC __hexa_parser_ic_312 = {0};
static HexaIC __hexa_parser_ic_313 = {0};
static HexaIC __hexa_parser_ic_314 = {0};
static HexaIC __hexa_parser_ic_315 = {0};
static HexaIC __hexa_parser_ic_316 = {0};
static HexaIC __hexa_parser_ic_317 = {0};
static HexaIC __hexa_parser_ic_318 = {0};
static HexaIC __hexa_parser_ic_319 = {0};
static HexaIC __hexa_parser_ic_320 = {0};
static HexaIC __hexa_parser_ic_321 = {0};
static HexaIC __hexa_parser_ic_322 = {0};
static HexaIC __hexa_parser_ic_323 = {0};
static HexaIC __hexa_parser_ic_324 = {0};
static HexaIC __hexa_parser_ic_325 = {0};

HexaVal empty_node(void) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal node_int_lit(HexaVal val) {
    HexaVal n = empty_node();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("IntLit")), "name", hexa_str("")), "value", val), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal node_float_lit(HexaVal val) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("FloatLit")), "name", hexa_str("")), "value", val), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal node_bool_lit(HexaVal val) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BoolLit")), "name", hexa_str("")), "value", val), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal node_string_lit(HexaVal val) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("StringLit")), "name", hexa_str("")), "value", val), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal node_char_lit(HexaVal val) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("CharLit")), "name", hexa_str("")), "value", val), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal node_ident(HexaVal name) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Ident")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal node_wildcard(void) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Wildcard")), "name", hexa_str("_")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal p_record_error(HexaVal line, HexaVal col, HexaVal message) {
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(p_errors))); HexaVal __r=(p_max_errors); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        p_errors = hexa_array_push(p_errors, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "line", line), "col", col), "message", message));
    }
    return hexa_void();
}


HexaVal p_emit_parse_error(HexaVal tok, HexaVal msg) {
    HexaVal key = hexa_add(hexa_add(hexa_add(hexa_add(hexa_to_string(hexa_map_get_ic(tok, "line", &__hexa_parser_ic_0)), hexa_str(":")), hexa_to_string(hexa_map_get_ic(tok, "col", &__hexa_parser_ic_1))), hexa_str(":")), msg);
    if (hexa_truthy(hexa_eq(key, p_last_err_key))) {
        return hexa_int(0);
    }
    p_last_err_key = key;
    hexa_println(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Parse error at "), hexa_to_string(hexa_map_get_ic(tok, "line", &__hexa_parser_ic_2))), hexa_str(":")), hexa_to_string(hexa_map_get_ic(tok, "col", &__hexa_parser_ic_3))), hexa_str(": ")), msg));
    return hexa_int(1);
    return hexa_void();
}


HexaVal p_synchronize(void) {
    while (hexa_truthy(hexa_bool(!hexa_truthy(p_at_end())))) {
        HexaVal cur = p_peek();
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(cur, "kind", &__hexa_parser_ic_4), hexa_str("Newline")))) {
            p_advance();
            HexaVal next = p_peek();
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_5), hexa_str("Let")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_6), hexa_str("Const")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_7), hexa_str("Static")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_8), hexa_str("Fn")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_9), hexa_str("Struct")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_10), hexa_str("Enum")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_11), hexa_str("For")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_12), hexa_str("While")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_13), hexa_str("Loop")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_14), hexa_str("Do")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_15), hexa_str("Defer")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_16), hexa_str("Return")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_17), hexa_str("If")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_18), hexa_str("Match")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_19), hexa_str("Impl")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_20), hexa_str("Trait")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_21), hexa_str("Use")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_22), hexa_str("Mod")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_23), hexa_str("Try")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_24), hexa_str("Assert")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_25), hexa_str("Proof")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_26), hexa_str("At")))) {
                return hexa_bool(1);
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(next, "kind", &__hexa_parser_ic_27), hexa_str("Eof")))) {
                return hexa_bool(1);
            }
        } else {
            p_advance();
        }
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal p_get_errors(void) {
    return p_errors;
    return hexa_void();
}


HexaVal p_has_errors(void) {
    return hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(p_errors))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); }));
    return hexa_void();
}


HexaVal p_error_count(void) {
    return hexa_int(hexa_len(p_errors));
    return hexa_void();
}


HexaVal p_format_errors(void) {
    HexaVal lines = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(p_errors))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal e = hexa_index_get(p_errors, i);
        lines = hexa_array_push(lines, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("  error["), hexa_to_string(hexa_add(i, hexa_int(1)))), hexa_str("] ")), hexa_to_string(hexa_map_get_ic(e, "line", &__hexa_parser_ic_28))), hexa_str(":")), hexa_to_string(hexa_map_get_ic(e, "col", &__hexa_parser_ic_29))), hexa_str(" — ")), hexa_map_get_ic(e, "message", &__hexa_parser_ic_30)));
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_str_join(lines, hexa_str("\n"));
    return hexa_void();
}


HexaVal p_peek(void) {
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(p_pos); HexaVal __r=(hexa_int(hexa_len(p_tokens))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
        return Token(hexa_str("Eof"), hexa_str(""), hexa_int(0), hexa_int(0));
    }
    return hexa_index_get(p_tokens, p_pos);
    return hexa_void();
}


HexaVal p_peek_kind(void) {
    return hexa_map_get_ic(p_peek(), "kind", &__hexa_parser_ic_31);
    return hexa_void();
}


HexaVal p_peek_ahead(HexaVal offset) {
    HexaVal idx = hexa_add(p_pos, offset);
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(idx); HexaVal __r=(hexa_int(hexa_len(p_tokens))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
        return Token(hexa_str("Eof"), hexa_str(""), hexa_int(0), hexa_int(0));
    }
    return hexa_index_get(p_tokens, idx);
    return hexa_void();
}


HexaVal p_at_end(void) {
    return hexa_eq(p_peek_kind(), hexa_str("Eof"));
    return hexa_void();
}


HexaVal p_advance(void) {
    HexaVal tok = p_peek();
    p_pos = hexa_add(p_pos, hexa_int(1));
    return tok;
    return hexa_void();
}


HexaVal p_check(HexaVal expected_kind) {
    return hexa_eq(p_peek_kind(), expected_kind);
    return hexa_void();
}


HexaVal p_expect(HexaVal expected_kind) {
    if (hexa_truthy(p_check(expected_kind))) {
        return p_advance();
    }
    HexaVal tok = p_peek();
    HexaVal msg = hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("expected "), expected_kind), hexa_str(", got ")), hexa_map_get_ic(tok, "kind", &__hexa_parser_ic_32)), hexa_str(" ('")), hexa_map_get_ic(tok, "value", &__hexa_parser_ic_33)), hexa_str("')"));
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(p_errors))); HexaVal __r=(p_max_errors); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
        hexa_throw(hexa_str("too many parse errors"));
    }
    p_record_error(hexa_map_get_ic(tok, "line", &__hexa_parser_ic_34), hexa_map_get_ic(tok, "col", &__hexa_parser_ic_35), msg);
    p_emit_parse_error(tok, msg);
    return tok;
    return hexa_void();
}


HexaVal p_expect_ident(void) {
    HexaVal tok = p_peek();
    if (hexa_truthy(hexa_eq(hexa_map_get_ic(tok, "kind", &__hexa_parser_ic_36), hexa_str("Ident")))) {
        p_pos = hexa_add(p_pos, hexa_int(1));
        return hexa_map_get_ic(tok, "value", &__hexa_parser_ic_37);
    }
    HexaVal msg2 = hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("expected identifier, got "), hexa_map_get_ic(tok, "kind", &__hexa_parser_ic_38)), hexa_str(" ('")), hexa_map_get_ic(tok, "value", &__hexa_parser_ic_39)), hexa_str("')"));
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(p_errors))); HexaVal __r=(p_max_errors); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
        hexa_throw(hexa_str("too many parse errors"));
    }
    p_record_error(hexa_map_get_ic(tok, "line", &__hexa_parser_ic_40), hexa_map_get_ic(tok, "col", &__hexa_parser_ic_41), msg2);
    p_emit_parse_error(tok, msg2);
    return hexa_str("");
    return hexa_void();
}


HexaVal p_skip_newlines(void) {
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Newline"))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Semicolon")))))) {
        p_pos = hexa_add(p_pos, hexa_int(1));
    }
    return hexa_void();
}


HexaVal p_continue_bin_op(HexaVal kinds) {
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Newline")))))) {
        return hexa_bool(0);
    }
    HexaVal _o = hexa_int(1);
    while (hexa_truthy(hexa_bool(1))) {
        HexaVal _t = p_peek_ahead(_o);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(_t, "kind", &__hexa_parser_ic_42), hexa_str("Newline"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(_t, "kind", &__hexa_parser_ic_43), hexa_str("Semicolon")))))))) {
            HexaVal _i = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(_i); HexaVal __r=(hexa_int(hexa_len(kinds))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                if (hexa_truthy(hexa_eq(hexa_map_get_ic(_t, "kind", &__hexa_parser_ic_44), hexa_index_get(kinds, _i)))) {
                    p_skip_newlines();
                    return hexa_bool(1);
                }
                _i = hexa_add(_i, hexa_int(1));
            }
            return hexa_bool(0);
        }
        _o = hexa_add(_o, hexa_int(1));
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal is_comparison_op(HexaVal k) {
    if (hexa_truthy(hexa_eq(k, hexa_str("Lt")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Gt")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Le")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Ge")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("EqEq")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("NotEq")))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal parse(HexaVal tokens) {
    p_tokens = tokens;
    p_pos = hexa_int(0);
    p_pending_symbol = hexa_str("");
    p_pending_link = hexa_str("");
    p_pending_contract_requires = hexa_str("");
    p_pending_contract_ensures = hexa_str("");
    p_pending_contract_req_text = hexa_str("");
    p_pending_contract_ens_text = hexa_str("");
    p_errors = hexa_array_new();
    p_max_errors = hexa_int(50);
    p_last_err_key = hexa_str("");
    HexaVal stmts = hexa_array_new();
    p_skip_newlines();
    while (hexa_truthy(hexa_bool(!hexa_truthy(p_at_end())))) {
        if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(p_errors))); HexaVal __r=(p_max_errors); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
            return stmts;
        }
        HexaVal prev_pos = p_pos;
        HexaVal parse_ok = hexa_bool(1);
        {
            jmp_buf __jb; HexaVal __err = hexa_void();
            if (setjmp(__jb) == 0) {
                __hexa_try_push(&__jb);
                stmts = hexa_array_push(stmts, parse_stmt());
                __hexa_try_pop();
            } else {
                __err = __hexa_last_error();
                HexaVal parse_err = __err;
                HexaVal err_tok = p_peek();
                p_record_error(hexa_map_get_ic(err_tok, "line", &__hexa_parser_ic_45), hexa_map_get_ic(err_tok, "col", &__hexa_parser_ic_46), hexa_to_string(parse_err));
                p_synchronize();
                parse_ok = hexa_bool(0);
            }
        }
        if (hexa_truthy(hexa_eq(p_pos, prev_pos))) {
            p_advance();
        }
        p_skip_newlines();
    }
    return stmts;
    return hexa_void();
}


HexaVal parse_strict(HexaVal tokens) {
    p_tokens = tokens;
    p_pos = hexa_int(0);
    p_pending_symbol = hexa_str("");
    p_pending_link = hexa_str("");
    p_errors = hexa_array_new();
    p_max_errors = hexa_int(50);
    HexaVal stmts = hexa_array_new();
    p_skip_newlines();
    while (hexa_truthy(hexa_bool(!hexa_truthy(p_at_end())))) {
        stmts = hexa_array_push(stmts, parse_stmt());
        p_skip_newlines();
    }
    return stmts;
    return hexa_void();
}


HexaVal parse_stmt(void) {
    HexaVal tok = hexa_void();
    HexaVal rhs = hexa_void();
    HexaVal op_tok = hexa_void();
    HexaVal op_str = hexa_void();
    p_skip_newlines();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Pub")))) {
        parse_visibility();
    }
    while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("At")))) {
        p_advance();
        HexaVal next_tok = p_peek();
        HexaVal attr_name = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Ident")))) {
            attr_name = p_expect_ident();
        } else {
            attr_name = hexa_map_get_ic(next_tok, "value", &__hexa_parser_ic_47);
            p_advance();
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(attr_name, hexa_str("invariant"))) && hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace")))))) {
            return parse_invariant_decl();
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(attr_name, hexa_str("contract"))) && hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))))) {
            p_advance();
            p_pending_contract_requires = hexa_str("");
            p_pending_contract_ensures = hexa_str("");
            p_pending_contract_req_text = hexa_str("");
            p_pending_contract_ens_text = hexa_str("");
            while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
                HexaVal clause_tok = p_advance();
                HexaVal clause_name = hexa_map_get_ic(clause_tok, "value", &__hexa_parser_ic_48);
                if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
                    p_advance();
                }
                HexaVal expr_start = p_pos;
                HexaVal clause_expr = parse_expr();
                HexaVal src_text = hexa_str("");
                HexaVal _si = expr_start;
                while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(_si); HexaVal __r=(p_pos); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(src_text, hexa_str("")))))) {
                        src_text = hexa_add(src_text, hexa_str(" "));
                    }
                    src_text = hexa_add(src_text, hexa_map_get_ic(hexa_index_get(p_tokens, _si), "value", &__hexa_parser_ic_49));
                    _si = hexa_add(_si, hexa_int(1));
                }
                if (hexa_truthy(hexa_eq(clause_name, hexa_str("requires")))) {
                    p_pending_contract_requires = clause_expr;
                    p_pending_contract_req_text = src_text;
                } else {
                    if (hexa_truthy(hexa_eq(clause_name, hexa_str("ensures")))) {
                        p_pending_contract_ensures = clause_expr;
                        p_pending_contract_ens_text = src_text;
                    }
                }
                if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                    p_advance();
                }
            }
            p_expect(hexa_str("RParen"));
            if (hexa_truthy(hexa_eq(p_pending_attrs, hexa_str("")))) {
                p_pending_attrs = hexa_str("contract");
            } else {
                p_pending_attrs = hexa_add(p_pending_attrs, hexa_str(",contract"));
            }
        } else {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(attr_name, hexa_str("symbol"))) || hexa_truthy(hexa_eq(attr_name, hexa_str("link")))))) {
                HexaVal attr_arg = hexa_str("");
                if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
                    p_advance();
                    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen")))))) {
                        tok = p_advance();
                        attr_arg = hexa_map_get_ic(tok, "value", &__hexa_parser_ic_50);
                        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
                            p_advance();
                        }
                    }
                    p_expect(hexa_str("RParen"));
                }
                if (hexa_truthy(hexa_eq(attr_name, hexa_str("symbol")))) {
                    p_pending_symbol = attr_arg;
                } else {
                    p_pending_link = attr_arg;
                }
            } else {
                if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
                    p_advance();
                    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen")))))) {
                        tok = p_advance();
                        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
                            p_advance();
                        }
                    }
                    p_expect(hexa_str("RParen"));
                }
                if (hexa_truthy(hexa_eq(p_pending_attrs, hexa_str("")))) {
                    p_pending_attrs = attr_name;
                } else {
                    p_pending_attrs = hexa_add(hexa_add(p_pending_attrs, hexa_str(",")), attr_name);
                }
            }
        }
        p_skip_newlines();
    }
    HexaVal kind = p_peek_kind();
    if (hexa_truthy(hexa_eq(kind, hexa_str("Let")))) {
        return parse_let();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Const")))) {
        return parse_const();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Static")))) {
        return parse_static();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Fn")))) {
        return parse_fn_decl();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Struct")))) {
        return parse_struct_decl();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Enum")))) {
        return parse_enum_decl();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("For")))) {
        return parse_for_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("While")))) {
        return parse_while_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Loop")))) {
        return parse_loop_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Do")))) {
        return parse_do_while_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Defer")))) {
        return parse_defer_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Return")))) {
        return parse_return();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Proof")))) {
        return parse_proof_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Assert")))) {
        return parse_assert_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Invariant")))) {
        return parse_invariant_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Impl")))) {
        return parse_impl_block();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Trait")))) {
        return parse_trait_decl();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Use")))) {
        return parse_use_decl();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Mod")))) {
        return parse_mod_decl();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Ident")))) {
        tok = p_peek();
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(tok, "value", &__hexa_parser_ic_51), hexa_str("import")))) {
            p_advance();
            HexaVal path = hexa_str("");
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("StringLit")))) {
                HexaVal str_tok = p_advance();
                path = hexa_map_get_ic(str_tok, "value", &__hexa_parser_ic_52);
            }
            return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ImportStmt")), "name", path), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        }
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Try")))) {
        return parse_try_catch();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Throw")))) {
        return parse_throw_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Panic")))) {
        return parse_panic_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Drop")))) {
        return parse_drop_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Spawn")))) {
        return parse_spawn_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Scope")))) {
        return parse_scope_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Select")))) {
        return parse_select_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Async")))) {
        return parse_async_fn();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Extern")))) {
        return parse_extern_fn();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Type")))) {
        return parse_type_alias();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Atomic")))) {
        return parse_atomic_let();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Break")))) {
        return parse_break_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Continue")))) {
        return parse_continue_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Yield")))) {
        return parse_yield_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Comptime")))) {
        return parse_comptime_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Intent")))) {
        return parse_intent_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Verify")))) {
        return parse_verify_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Generate")))) {
        return parse_generate_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Optimize")))) {
        return parse_optimize_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Effect")))) {
        return parse_effect_decl();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Pure")))) {
        return parse_pure_fn();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Macro")))) {
        return parse_macro_def();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Derive")))) {
        return parse_derive_decl();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Theorem")))) {
        return parse_theorem_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Handle")))) {
        return parse_handle_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Recover")))) {
        return parse_recover_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Resume")))) {
        return parse_resume_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Guard")))) {
        return parse_guard_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("With")))) {
        return parse_with_stmt();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Label")))) {
        return parse_labeled_loop();
    }
    if (hexa_truthy(hexa_eq(kind, hexa_str("Attribute")))) {
        return parse_attribute_prefix();
    }
    HexaVal expr = parse_expr();
    HexaVal pk = p_peek_kind();
    if (hexa_truthy(hexa_eq(pk, hexa_str("Eq")))) {
        p_advance();
        rhs = parse_expr();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("AssignStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", rhs), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(pk, hexa_str("PlusEq"))) || hexa_truthy(hexa_eq(pk, hexa_str("MinusEq"))))) || hexa_truthy(hexa_eq(pk, hexa_str("StarEq"))))) || hexa_truthy(hexa_eq(pk, hexa_str("SlashEq"))))) || hexa_truthy(hexa_eq(pk, hexa_str("PercentEq")))))) {
        op_tok = p_advance();
        op_str = (hexa_truthy(hexa_eq(pk, hexa_str("PlusEq"))) ? hexa_str("+") : (hexa_truthy(hexa_eq(pk, hexa_str("MinusEq"))) ? hexa_str("-") : (hexa_truthy(hexa_eq(pk, hexa_str("StarEq"))) ? hexa_str("*") : (hexa_truthy(hexa_eq(pk, hexa_str("SlashEq"))) ? hexa_str("/") : hexa_str("%")))));
        rhs = parse_expr();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("CompoundAssign")), "name", hexa_str("")), "value", hexa_str("")), "op", op_str), "left", expr), "right", rhs), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(pk, hexa_str("NullCoalescingAssign"))) || hexa_truthy(hexa_eq(pk, hexa_str("OrAssign"))))) || hexa_truthy(hexa_eq(pk, hexa_str("AndAssign")))))) {
        op_tok = p_advance();
        op_str = (hexa_truthy(hexa_eq(pk, hexa_str("NullCoalescingAssign"))) ? hexa_str("??=") : (hexa_truthy(hexa_eq(pk, hexa_str("OrAssign"))) ? hexa_str("||=") : hexa_str("&&=")));
        rhs = parse_expr();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("LogicalAssign")), "name", hexa_str("")), "value", hexa_str("")), "op", op_str), "left", expr), "right", rhs), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ExprStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_let(void) {
    HexaVal patterns = hexa_void();
    HexaVal expr = hexa_void();
    p_advance();
    HexaVal is_mut = hexa_bool(0);
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Mut")))) {
        p_advance();
        is_mut = hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBracket")))) {
        p_advance();
        patterns = hexa_array_new();
        HexaVal rest_name = hexa_str("");
        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBracket"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("DotDotDot")))) {
                p_advance();
                rest_name = p_expect_ident();
            } else {
                patterns = hexa_array_push(patterns, p_expect_ident());
            }
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                p_advance();
            }
        }
        p_expect(hexa_str("RBracket"));
        p_expect(hexa_str("Eq"));
        expr = parse_expr();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("DestructLetStmt")), "name", rest_name), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", patterns), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace")))) {
        p_advance();
        patterns = hexa_array_new();
        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
            patterns = hexa_array_push(patterns, p_expect_ident());
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                p_advance();
            }
        }
        p_expect(hexa_str("RBrace"));
        p_expect(hexa_str("Eq"));
        expr = parse_expr();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("MapDestructLetStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", patterns), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    HexaVal name = p_expect_ident();
    HexaVal typ = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
        p_advance();
        typ = parse_type_annotation();
    }
    p_expect(hexa_str("Eq"));
    expr = parse_expr();
    HexaVal kind_str = hexa_str("LetStmt");
    if (hexa_truthy(is_mut)) {
        kind_str = hexa_str("LetMutStmt");
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", kind_str), "name", name), "value", typ), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_const(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    HexaVal typ = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
        p_advance();
        typ = parse_type_annotation();
    }
    p_expect(hexa_str("Eq"));
    HexaVal expr = parse_expr();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ConstStmt")), "name", name), "value", typ), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_static(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    HexaVal typ = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
        p_advance();
        typ = parse_type_annotation();
    }
    p_expect(hexa_str("Eq"));
    HexaVal expr = parse_expr();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("StaticStmt")), "name", name), "value", typ), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_return(void) {
    p_advance();
    HexaVal k = p_peek_kind();
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("Newline"))) || hexa_truthy(hexa_eq(k, hexa_str("Eof"))))) || hexa_truthy(hexa_eq(k, hexa_str("RBrace")))))) {
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ReturnStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    HexaVal expr = parse_expr();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ReturnStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_proof_stmt(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ProofStmt")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_assert_stmt(void) {
    p_advance();
    HexaVal expr = parse_expr();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("AssertStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_resume_stmt(void) {
    p_advance();
    HexaVal expr = parse_expr();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Resume")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_invariant_stmt(void) {
    p_advance();
    HexaVal expr = parse_expr();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Invariant")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_invariant_decl(void) {
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal id_str = hexa_str("");
    HexaVal name_str = hexa_str("");
    HexaVal pred_str = hexa_str("");
    HexaVal tgt_str = hexa_str("");
    HexaVal ctx_str = hexa_str("");
    HexaVal exempt_list = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        HexaVal key_tok = p_peek();
        HexaVal key_name = hexa_str("");
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(key_tok, "kind", &__hexa_parser_ic_53), hexa_str("Ident")))) {
            p_advance();
            key_name = hexa_map_get_ic(key_tok, "value", &__hexa_parser_ic_54);
        } else {
            p_advance();
            key_name = hexa_map_get_ic(key_tok, "value", &__hexa_parser_ic_55);
        }
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
            p_advance();
        }
        HexaVal vk = p_peek_kind();
        if (hexa_truthy(hexa_eq(vk, hexa_str("StringLit")))) {
            HexaVal vt = p_advance();
            if (hexa_truthy(hexa_eq(key_name, hexa_str("id")))) {
                id_str = hexa_map_get_ic(vt, "value", &__hexa_parser_ic_56);
            } else {
                if (hexa_truthy(hexa_eq(key_name, hexa_str("name")))) {
                    name_str = hexa_map_get_ic(vt, "value", &__hexa_parser_ic_57);
                } else {
                    if (hexa_truthy(hexa_eq(key_name, hexa_str("predicate")))) {
                        pred_str = hexa_map_get_ic(vt, "value", &__hexa_parser_ic_58);
                    } else {
                        if (hexa_truthy(hexa_eq(key_name, hexa_str("target")))) {
                            tgt_str = hexa_map_get_ic(vt, "value", &__hexa_parser_ic_59);
                        } else {
                            if (hexa_truthy(hexa_eq(key_name, hexa_str("context")))) {
                                ctx_str = hexa_map_get_ic(vt, "value", &__hexa_parser_ic_60);
                            }
                        }
                    }
                }
            }
        } else {
            if (hexa_truthy(hexa_eq(vk, hexa_str("LBrace")))) {
                p_advance();
                p_skip_newlines();
                while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
                    HexaVal nk_tok = p_peek();
                    HexaVal nk = hexa_str("");
                    if (hexa_truthy(hexa_eq(hexa_map_get_ic(nk_tok, "kind", &__hexa_parser_ic_61), hexa_str("Ident")))) {
                        p_advance();
                        nk = hexa_map_get_ic(nk_tok, "value", &__hexa_parser_ic_62);
                    } else {
                        p_advance();
                        nk = hexa_map_get_ic(nk_tok, "value", &__hexa_parser_ic_63);
                    }
                    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
                        p_advance();
                    }
                    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("StringLit")))) {
                        HexaVal nv = p_advance();
                        if (hexa_truthy(hexa_eq(key_name, hexa_str("pattern")))) {
                            if (hexa_truthy(hexa_eq(nk, hexa_str("target")))) {
                                tgt_str = hexa_map_get_ic(nv, "value", &__hexa_parser_ic_64);
                            } else {
                                if (hexa_truthy(hexa_eq(nk, hexa_str("context")))) {
                                    ctx_str = hexa_map_get_ic(nv, "value", &__hexa_parser_ic_65);
                                }
                            }
                        }
                    } else {
                        p_advance();
                    }
                    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                        p_advance();
                    }
                    p_skip_newlines();
                }
                p_expect(hexa_str("RBrace"));
            } else {
                if (hexa_truthy(hexa_eq(vk, hexa_str("LBracket")))) {
                    p_advance();
                    p_skip_newlines();
                    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBracket"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
                        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("StringLit")))) {
                            HexaVal et = p_advance();
                            if (hexa_truthy(hexa_eq(key_name, hexa_str("exempt")))) {
                                exempt_list = hexa_array_push(exempt_list, hexa_map_get_ic(et, "value", &__hexa_parser_ic_66));
                            }
                        } else {
                            p_advance();
                        }
                        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                            p_advance();
                        }
                        p_skip_newlines();
                    }
                    p_expect(hexa_str("RBracket"));
                } else {
                    p_advance();
                }
            }
        }
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
            p_advance();
        }
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("InvariantDecl")), "name", id_str), "value", name_str), "op", pred_str), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", exempt_list), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", tgt_str), "trait_name", ctx_str), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_use_decl(void) {
    p_advance();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("StringLit")))) {
        HexaVal str_tok = p_advance();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("UseStmt")), "name", hexa_map_get_ic(str_tok, "value", &__hexa_parser_ic_67)), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_array_push(hexa_array_new(), hexa_map_get_ic(str_tok, "value", &__hexa_parser_ic_68))), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    HexaVal path = hexa_array_new();
    path = hexa_array_push(path, p_expect_ident());
    while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("ColonColon")))) {
        p_advance();
        path = hexa_array_push(path, p_expect_ident());
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("UseStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", path), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_mod_decl(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ModStmt")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_fn_decl(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    HexaVal tparams = hexa_array_new();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Lt")))) {
        tparams = parse_type_params();
    }
    p_expect(hexa_str("LParen"));
    HexaVal params = parse_params();
    p_expect(hexa_str("RParen"));
    HexaVal ret = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
        p_advance();
        ret = parse_type_annotation();
    }
    HexaVal body = parse_block();
    HexaVal attrs = p_pending_attrs;
    p_pending_attrs = hexa_str("");
    HexaVal final_body = body;
    HexaVal req_expr = p_pending_contract_requires;
    HexaVal ens_expr = p_pending_contract_ensures;
    HexaVal req_text = p_pending_contract_req_text;
    HexaVal ens_text = p_pending_contract_ens_text;
    p_pending_contract_requires = hexa_str("");
    p_pending_contract_ensures = hexa_str("");
    p_pending_contract_req_text = hexa_str("");
    p_pending_contract_ens_text = hexa_str("");
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(req_expr, hexa_str("")))))) {
        HexaVal req_node = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ContractAssert")), "name", name), "value", hexa_add(hexa_str("requires: "), req_text)), "op", hexa_str("requires")), "left", req_expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        HexaVal new_body = hexa_array_push(hexa_array_new(), req_node);
        {
            HexaVal __iter_arr = final_body;
            for (int __fi = 0; __fi < hexa_len(__iter_arr); __fi++) {
                HexaVal stmt = hexa_iter_get(__iter_arr, __fi);
                new_body = hexa_array_push(new_body, stmt);
            }
        }
        final_body = new_body;
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(ens_expr, hexa_str("")))))) {
        final_body = contract_wrap_returns(final_body, ens_expr, name, ens_text);
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("FnDecl")), "name", name), "value", attrs), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", params), "body", final_body), "args", hexa_str("")), "fields", hexa_str("")), "items", tparams), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", ret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal contract_wrap_returns(HexaVal body, HexaVal ens_expr, HexaVal fn_name, HexaVal ens_text) {
    HexaVal out = hexa_array_new();
    {
        HexaVal __iter_arr = body;
        for (int __fi = 0; __fi < hexa_len(__iter_arr); __fi++) {
            HexaVal stmt = hexa_iter_get(__iter_arr, __fi);
            if (hexa_truthy(hexa_eq(hexa_type_of(stmt), hexa_str("string")))) {
                out = hexa_array_push(out, stmt);
            } else {
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_map_get_ic(stmt, "kind", &__hexa_parser_ic_69), hexa_str("ReturnStmt"))) || hexa_truthy(hexa_eq(hexa_map_get_ic(stmt, "kind", &__hexa_parser_ic_70), hexa_str("Return")))))) {
                    HexaVal let_node = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("LetStmt")), "name", hexa_str("__contract_result")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_map_get_ic(stmt, "left", &__hexa_parser_ic_71)), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                    HexaVal assert_node = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ContractAssert")), "name", fn_name), "value", hexa_add(hexa_str("ensures: "), ens_text)), "op", hexa_str("ensures")), "left", ens_expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                    HexaVal ret_node = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ReturnStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", node_ident(hexa_str("__contract_result"))), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                    out = hexa_array_push(out, let_node);
                    out = hexa_array_push(out, assert_node);
                    out = hexa_array_push(out, ret_node);
                } else {
                    if (hexa_truthy(hexa_eq(hexa_map_get_ic(stmt, "kind", &__hexa_parser_ic_72), hexa_str("IfStmt")))) {
                        HexaVal wrapped = stmt;
                        if (hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(stmt, "then_body", &__hexa_parser_ic_73)), hexa_str("array")))) {
                            wrapped = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("IfStmt")), "name", hexa_map_get_ic(stmt, "name", &__hexa_parser_ic_74)), "value", hexa_map_get_ic(stmt, "value", &__hexa_parser_ic_75)), "op", hexa_map_get_ic(stmt, "op", &__hexa_parser_ic_76)), "left", hexa_map_get_ic(stmt, "left", &__hexa_parser_ic_77)), "right", hexa_map_get_ic(stmt, "right", &__hexa_parser_ic_78)), "cond", hexa_map_get_ic(stmt, "cond", &__hexa_parser_ic_79)), "then_body", contract_wrap_returns(hexa_map_get_ic(stmt, "then_body", &__hexa_parser_ic_80), ens_expr, fn_name, ens_text)), "else_body", hexa_map_get_ic(stmt, "else_body", &__hexa_parser_ic_81)), "params", hexa_map_get_ic(stmt, "params", &__hexa_parser_ic_82)), "body", hexa_map_get_ic(stmt, "body", &__hexa_parser_ic_83)), "args", hexa_map_get_ic(stmt, "args", &__hexa_parser_ic_84)), "fields", hexa_map_get_ic(stmt, "fields", &__hexa_parser_ic_85)), "items", hexa_map_get_ic(stmt, "items", &__hexa_parser_ic_86)), "variants", hexa_map_get_ic(stmt, "variants", &__hexa_parser_ic_87)), "arms", hexa_map_get_ic(stmt, "arms", &__hexa_parser_ic_88)), "iter_expr", hexa_map_get_ic(stmt, "iter_expr", &__hexa_parser_ic_89)), "ret_type", hexa_map_get_ic(stmt, "ret_type", &__hexa_parser_ic_90)), "target", hexa_map_get_ic(stmt, "target", &__hexa_parser_ic_91)), "trait_name", hexa_map_get_ic(stmt, "trait_name", &__hexa_parser_ic_92)), "methods", hexa_map_get_ic(stmt, "methods", &__hexa_parser_ic_93));
                        }
                        if (hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(wrapped, "else_body", &__hexa_parser_ic_94)), hexa_str("array")))) {
                            wrapped = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("IfStmt")), "name", hexa_map_get_ic(wrapped, "name", &__hexa_parser_ic_95)), "value", hexa_map_get_ic(wrapped, "value", &__hexa_parser_ic_96)), "op", hexa_map_get_ic(wrapped, "op", &__hexa_parser_ic_97)), "left", hexa_map_get_ic(wrapped, "left", &__hexa_parser_ic_98)), "right", hexa_map_get_ic(wrapped, "right", &__hexa_parser_ic_99)), "cond", hexa_map_get_ic(wrapped, "cond", &__hexa_parser_ic_100)), "then_body", hexa_map_get_ic(wrapped, "then_body", &__hexa_parser_ic_101)), "else_body", contract_wrap_returns(hexa_map_get_ic(wrapped, "else_body", &__hexa_parser_ic_102), ens_expr, fn_name, ens_text)), "params", hexa_map_get_ic(wrapped, "params", &__hexa_parser_ic_103)), "body", hexa_map_get_ic(wrapped, "body", &__hexa_parser_ic_104)), "args", hexa_map_get_ic(wrapped, "args", &__hexa_parser_ic_105)), "fields", hexa_map_get_ic(wrapped, "fields", &__hexa_parser_ic_106)), "items", hexa_map_get_ic(wrapped, "items", &__hexa_parser_ic_107)), "variants", hexa_map_get_ic(wrapped, "variants", &__hexa_parser_ic_108)), "arms", hexa_map_get_ic(wrapped, "arms", &__hexa_parser_ic_109)), "iter_expr", hexa_map_get_ic(wrapped, "iter_expr", &__hexa_parser_ic_110)), "ret_type", hexa_map_get_ic(wrapped, "ret_type", &__hexa_parser_ic_111)), "target", hexa_map_get_ic(wrapped, "target", &__hexa_parser_ic_112)), "trait_name", hexa_map_get_ic(wrapped, "trait_name", &__hexa_parser_ic_113)), "methods", hexa_map_get_ic(wrapped, "methods", &__hexa_parser_ic_114));
                        }
                        out = hexa_array_push(out, wrapped);
                    } else {
                        out = hexa_array_push(out, stmt);
                    }
                }
            }
        }
    }
    return out;
    return hexa_void();
}


HexaVal parse_type_annotation(void) {
    HexaVal base = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Star")))) {
        p_advance();
        base = hexa_add(hexa_str("*"), p_expect_ident());
    } else {
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBracket")))) {
            p_advance();
            HexaVal inner = parse_type_annotation();
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Semicolon")))) {
                p_advance();
                if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBracket")))))) {
                    p_advance();
                }
            }
            p_expect(hexa_str("RBracket"));
            base = hexa_add(hexa_add(hexa_str("["), inner), hexa_str("]"));
        } else {
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
                p_advance();
                HexaVal parts = hexa_array_new();
                if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen")))))) {
                    parts = hexa_array_push(parts, parse_type_annotation());
                    while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                        p_advance();
                        parts = hexa_array_push(parts, parse_type_annotation());
                    }
                }
                p_expect(hexa_str("RParen"));
                base = hexa_add(hexa_add(hexa_str("("), hexa_str_join(parts, hexa_str(", "))), hexa_str(")"));
            } else {
                base = p_expect_ident();
            }
        }
    }
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Question")))) {
        p_advance();
        base = hexa_add(base, hexa_str("?"));
    }
    while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("BitOr")))) {
        p_advance();
        HexaVal next = parse_type_annotation();
        base = hexa_add(hexa_add(base, hexa_str(" | ")), next);
    }
    return base;
    return hexa_void();
}


HexaVal parse_params(void) {
    HexaVal params = hexa_array_new();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen")))) {
        return params;
    }
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Mut")))) {
        p_advance();
    }
    HexaVal name = p_expect_ident();
    HexaVal typ = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
        p_advance();
        typ = parse_type_annotation();
    }
    params = hexa_array_push(params, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Param")), "name", name), "value", typ), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
    while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
        p_advance();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Mut")))) {
            p_advance();
        }
        HexaVal pname = p_expect_ident();
        HexaVal ptyp = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
            p_advance();
            ptyp = parse_type_annotation();
        }
        params = hexa_array_push(params, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Param")), "name", pname), "value", ptyp), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
    }
    return params;
    return hexa_void();
}


HexaVal parse_struct_decl(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    HexaVal tparams = hexa_array_new();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Lt")))) {
        tparams = parse_type_params();
    }
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal fields = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        HexaVal fname = p_expect_ident();
        HexaVal ftype = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
            p_advance();
            ftype = parse_type_annotation();
        }
        fields = hexa_array_push(fields, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("StructField")), "name", fname), "value", ftype), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
            p_advance();
        }
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("StructDecl")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", fields), "items", tparams), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_enum_decl(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal variants = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        HexaVal vname = p_expect_ident();
        HexaVal vtypes = hexa_array_new();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
            p_advance();
            while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
                vtypes = hexa_array_push(vtypes, p_expect_ident());
                if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                    p_advance();
                }
            }
            p_expect(hexa_str("RParen"));
        }
        variants = hexa_array_push(variants, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("EnumVariant")), "name", vname), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", vtypes), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
            p_advance();
        }
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("EnumDecl")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", variants), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_trait_decl(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal methods = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        p_skip_newlines();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace")))) {
        } else {
            p_expect(hexa_str("Fn"));
            HexaVal mname = p_expect_ident();
            p_expect(hexa_str("LParen"));
            HexaVal mparams = parse_params();
            p_expect(hexa_str("RParen"));
            HexaVal mret = hexa_str("");
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
                p_advance();
                mret = parse_type_annotation();
            }
            HexaVal mbody = hexa_array_new();
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace")))) {
                mbody = parse_block();
            }
            methods = hexa_array_push(methods, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("FnDecl")), "name", mname), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", mparams), "body", mbody), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", mret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
            p_skip_newlines();
        }
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("TraitDecl")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", methods);
    return hexa_void();
}


HexaVal parse_impl_block(void) {
    p_advance();
    HexaVal first_name = p_expect_ident();
    HexaVal trait_n = hexa_str("");
    HexaVal target_n = first_name;
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("For")))) {
        p_advance();
        trait_n = first_name;
        target_n = p_expect_ident();
    }
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal methods = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        p_skip_newlines();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace")))) {
        } else {
            p_expect(hexa_str("Fn"));
            HexaVal mname = p_expect_ident();
            p_expect(hexa_str("LParen"));
            HexaVal mparams = parse_params();
            p_expect(hexa_str("RParen"));
            HexaVal mret = hexa_str("");
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
                p_advance();
                mret = parse_type_annotation();
            }
            HexaVal mbody = parse_block();
            methods = hexa_array_push(methods, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("FnDecl")), "name", mname), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", mparams), "body", mbody), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", mret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
            p_skip_newlines();
        }
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ImplBlock")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", target_n), "trait_name", trait_n), "methods", methods);
    return hexa_void();
}


HexaVal parse_for_stmt(void) {
    p_advance();
    HexaVal var = p_expect_ident();
    HexaVal in_tok = p_advance();
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(in_tok, "value", &__hexa_parser_ic_115), hexa_str("in")))))) {
        HexaVal for_msg = hexa_format_n(hexa_str("expected 'in' after for variable, got '{}'"), hexa_array_push(hexa_array_new(), hexa_map_get_ic(in_tok, "value", &__hexa_parser_ic_116)));
        p_record_error(hexa_map_get_ic(in_tok, "line", &__hexa_parser_ic_117), hexa_map_get_ic(in_tok, "col", &__hexa_parser_ic_118), for_msg);
        hexa_println(hexa_add(hexa_str("Parse error: "), for_msg));
    }
    HexaVal prev_supp = p_suppress_struct_lit;
    p_suppress_struct_lit = hexa_bool(1);
    HexaVal iter = parse_expr();
    p_suppress_struct_lit = prev_supp;
    HexaVal body = parse_block();
    HexaVal saved = p_pos;
    p_skip_newlines();
    HexaVal else_body = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Else")))) {
        p_advance();
        else_body = parse_block();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ForElseStmt")), "name", var), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", else_body), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", iter), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    } else {
        p_pos = saved;
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ForStmt")), "name", var), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", iter), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_while_stmt(void) {
    p_advance();
    HexaVal prev_supp = p_suppress_struct_lit;
    p_suppress_struct_lit = hexa_bool(1);
    HexaVal cond = parse_expr();
    p_suppress_struct_lit = prev_supp;
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("WhileStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", cond), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_loop_stmt(void) {
    p_advance();
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("LoopStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_if_expr(void) {
    HexaVal prev_supp = hexa_void();
    HexaVal then_b = hexa_void();
    HexaVal saved = hexa_void();
    HexaVal else_b = hexa_void();
    HexaVal nested = hexa_void();
    p_advance();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Let")))) {
        p_advance();
        HexaVal pattern = parse_match_pattern();
        p_expect(hexa_str("Eq"));
        prev_supp = p_suppress_struct_lit;
        p_suppress_struct_lit = hexa_bool(1);
        HexaVal scrutinee = parse_expr();
        p_suppress_struct_lit = prev_supp;
        then_b = parse_block();
        saved = p_pos;
        p_skip_newlines();
        else_b = hexa_array_new();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Else")))) {
            p_advance();
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("If")))) {
                nested = parse_if_expr();
                else_b = hexa_array_push(hexa_array_new(), hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ExprStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", nested), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
            } else {
                else_b = parse_block();
            }
        } else {
            p_pos = saved;
        }
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("IfLetExpr")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", pattern), "right", scrutinee), "cond", hexa_str("")), "then_body", then_b), "else_body", else_b), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    prev_supp = p_suppress_struct_lit;
    p_suppress_struct_lit = hexa_bool(1);
    HexaVal cond = parse_expr();
    p_suppress_struct_lit = prev_supp;
    then_b = parse_block();
    saved = p_pos;
    p_skip_newlines();
    else_b = hexa_array_new();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Else")))) {
        p_advance();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("If")))) {
            nested = parse_if_expr();
            else_b = hexa_array_push(hexa_array_new(), hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ExprStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", nested), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        } else {
            else_b = parse_block();
        }
    } else {
        p_pos = saved;
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("IfExpr")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", cond), "then_body", then_b), "else_body", else_b), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_match_expr(void) {
    p_advance();
    HexaVal prev_supp = p_suppress_struct_lit;
    p_suppress_struct_lit = hexa_bool(1);
    HexaVal scrutinee = parse_expr();
    p_suppress_struct_lit = prev_supp;
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal arms = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        HexaVal pattern = parse_match_pattern();
        HexaVal or_patterns = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("BitOr")))) {
            or_patterns = hexa_array_push(hexa_array_new(), pattern);
            while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("BitOr")))) {
                p_advance();
                or_patterns = hexa_array_push(or_patterns, parse_match_pattern());
            }
        }
        HexaVal guard_expr = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("If")))) {
            p_advance();
            guard_expr = parse_expr();
        }
        p_expect(hexa_str("Arrow"));
        HexaVal arm_body = hexa_array_new();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace")))) {
            arm_body = parse_block();
        } else {
            HexaVal arm_expr = parse_expr();
            arm_body = hexa_array_push(hexa_array_new(), hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ExprStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", arm_expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        }
        arms = hexa_array_push(arms, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("MatchArm")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", pattern), "right", hexa_str("")), "cond", guard_expr), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", arm_body), "args", hexa_str("")), "fields", hexa_str("")), "items", or_patterns), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
            p_advance();
        }
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("MatchExpr")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", scrutinee), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", arms), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_match_pattern(void) {
    HexaVal pat_items = hexa_void();
    HexaVal tok = p_peek();
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_map_get_ic(tok, "kind", &__hexa_parser_ic_119), hexa_str("Ident"))) && hexa_truthy(hexa_eq(hexa_map_get_ic(tok, "value", &__hexa_parser_ic_120), hexa_str("_")))))) {
        p_advance();
        return node_wildcard();
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_map_get_ic(tok, "kind", &__hexa_parser_ic_121), hexa_str("Ident"))) && hexa_truthy(hexa_eq(hexa_map_get_ic(p_peek_ahead(hexa_int(1)), "kind", &__hexa_parser_ic_122), hexa_str("ColonColon")))))) {
        HexaVal ename = hexa_map_get_ic(tok, "value", &__hexa_parser_ic_123);
        p_advance();
        p_advance();
        HexaVal vname = p_expect_ident();
        HexaVal data = hexa_str("");
        pat_items = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
            p_advance();
            HexaVal plist = hexa_array_new();
            while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
                plist = hexa_array_push(plist, parse_match_pattern());
                if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                    p_advance();
                }
            }
            p_expect(hexa_str("RParen"));
            if (hexa_truthy(hexa_eq(hexa_int(hexa_len(plist)), hexa_int(1)))) {
                data = hexa_index_get(plist, hexa_int(0));
            } else {
                pat_items = plist;
            }
        }
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("EnumPath")), "name", ename), "value", vname), "op", hexa_str("")), "left", data), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", pat_items), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(hexa_map_get_ic(tok, "kind", &__hexa_parser_ic_124), hexa_str("LBracket")))) {
        p_advance();
        pat_items = hexa_array_new();
        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBracket"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("DotDotDot")))) {
                p_advance();
                HexaVal rest_name = p_expect_ident();
                pat_items = hexa_array_push(pat_items, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("RestPattern")), "name", rest_name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
            } else {
                pat_items = hexa_array_push(pat_items, parse_match_pattern());
            }
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                p_advance();
            }
        }
        p_expect(hexa_str("RBracket"));
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Array")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", pat_items), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return parse_expr();
    return hexa_void();
}


HexaVal parse_guard_stmt(void) {
    HexaVal else_body = hexa_void();
    p_advance();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Let")))) {
        p_advance();
        HexaVal name = p_expect_ident();
        p_expect(hexa_str("Eq"));
        HexaVal expr = parse_expr();
        p_expect(hexa_str("Else"));
        else_body = parse_block();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("GuardLetStmt")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", else_body), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    HexaVal prev_supp = p_suppress_struct_lit;
    p_suppress_struct_lit = hexa_bool(1);
    HexaVal cond = parse_expr();
    p_suppress_struct_lit = prev_supp;
    p_expect(hexa_str("Else"));
    else_body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("GuardStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", cond), "then_body", hexa_str("")), "else_body", else_body), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_with_stmt(void) {
    p_advance();
    HexaVal expr = parse_expr();
    HexaVal name = hexa_str("_resource");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("As")))) {
        p_advance();
        name = p_expect_ident();
    }
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("WithStmt")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_block(void) {
    p_skip_newlines();
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal stmts = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        stmts = hexa_array_push(stmts, parse_stmt());
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return stmts;
    return hexa_void();
}


HexaVal parse_expr(void) {
    HexaVal left = parse_pipe();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("ColonEq")))) {
        p_advance();
        HexaVal right = parse_pipe();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("WalrusExpr")), "name", hexa_map_get_ic(left, "name", &__hexa_parser_ic_125)), "value", hexa_str("")), "op", hexa_str(":=")), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return left;
    return hexa_void();
}


HexaVal parse_pipe(void) {
    HexaVal left = parse_null_coal();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Pipe"))) || hexa_truthy(p_continue_bin_op(hexa_array_push(hexa_array_new(), hexa_str("Pipe"))))))) {
        HexaVal op_tok = p_advance();
        p_skip_newlines();
        HexaVal right = parse_null_coal();
        left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_126)), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return left;
    return hexa_void();
}


HexaVal parse_null_coal(void) {
    HexaVal left = parse_or();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("NullCoal"))) || hexa_truthy(p_continue_bin_op(hexa_array_push(hexa_array_new(), hexa_str("NullCoal"))))))) {
        HexaVal op_tok = p_advance();
        p_skip_newlines();
        HexaVal right = parse_or();
        left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_127)), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return left;
    return hexa_void();
}


HexaVal parse_or(void) {
    HexaVal left = parse_and();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Or"))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Xor"))))) || hexa_truthy(p_continue_bin_op(hexa_array_push(hexa_array_push(hexa_array_new(), hexa_str("Or")), hexa_str("Xor"))))))) {
        HexaVal op_tok = p_advance();
        p_skip_newlines();
        HexaVal right = parse_and();
        left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_128)), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return left;
    return hexa_void();
}


HexaVal parse_and(void) {
    HexaVal left = parse_bit_ops();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("And"))) || hexa_truthy(p_continue_bin_op(hexa_array_push(hexa_array_new(), hexa_str("And"))))))) {
        HexaVal op_tok = p_advance();
        p_skip_newlines();
        HexaVal right = parse_bit_ops();
        left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_129)), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return left;
    return hexa_void();
}


HexaVal parse_bit_ops(void) {
    HexaVal left = parse_comparison();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("BitAnd"))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("BitXor")))))) {
        HexaVal op_tok = p_advance();
        p_skip_newlines();
        HexaVal right = parse_comparison();
        left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_130)), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return left;
    return hexa_void();
}


HexaVal parse_comparison(void) {
    HexaVal left = parse_bitwise();
    if (hexa_truthy(hexa_bool(!hexa_truthy(is_comparison_op(p_peek_kind()))))) {
        return left;
    }
    HexaVal op_tok = p_advance();
    p_skip_newlines();
    HexaVal right = parse_bitwise();
    left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_131)), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    while (hexa_truthy(is_comparison_op(p_peek_kind()))) {
        HexaVal op2_tok = p_advance();
        p_skip_newlines();
        HexaVal middle = right;
        HexaVal next = parse_bitwise();
        HexaVal right_cmp = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op2_tok, "value", &__hexa_parser_ic_132)), "left", middle), "right", next), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("&&")), "left", left), "right", right_cmp), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        right = next;
    }
    return left;
    return hexa_void();
}


HexaVal parse_bitwise(void) {
    HexaVal right = hexa_void();
    HexaVal left = parse_addition();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("EqEq"))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("NotEq"))))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Lt"))))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Gt"))))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LtEq"))))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("GtEq"))))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("In"))))) || hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Ident"))) && hexa_truthy(hexa_eq(hexa_map_get_ic(p_peek(), "value", &__hexa_parser_ic_133), hexa_str("is"))))))) || hexa_truthy(p_continue_bin_op(hexa_array_push(hexa_array_push(hexa_array_push(hexa_array_push(hexa_array_push(hexa_array_push(hexa_array_new(), hexa_str("EqEq")), hexa_str("NotEq")), hexa_str("Lt")), hexa_str("Gt")), hexa_str("LtEq")), hexa_str("GtEq"))))))) {
        HexaVal op_tok = p_advance();
        p_skip_newlines();
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_134), hexa_str("is")))) {
            HexaVal type_tok = p_advance();
            right = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Ident")), "name", hexa_map_get_ic(type_tok, "value", &__hexa_parser_ic_135)), "value", hexa_map_get_ic(type_tok, "value", &__hexa_parser_ic_136)), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
            left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("is")), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        } else {
            right = parse_addition();
            left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_137)), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        }
    }
    return left;
    return hexa_void();
}


HexaVal parse_addition(void) {
    HexaVal left = parse_multiplication();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Plus"))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Minus"))))) || hexa_truthy(p_continue_bin_op(hexa_array_push(hexa_array_new(), hexa_str("Plus"))))))) {
        HexaVal op_tok = p_advance();
        p_skip_newlines();
        HexaVal right = parse_multiplication();
        left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_138)), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return left;
    return hexa_void();
}


HexaVal parse_multiplication(void) {
    HexaVal left = parse_unary();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Star"))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Slash"))))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Percent"))))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Power"))))) || hexa_truthy(p_continue_bin_op(hexa_array_push(hexa_array_push(hexa_array_push(hexa_array_push(hexa_array_new(), hexa_str("Star")), hexa_str("Slash")), hexa_str("Percent")), hexa_str("Power"))))))) {
        HexaVal op_tok = p_advance();
        p_skip_newlines();
        HexaVal right = parse_unary();
        left = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_139)), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return left;
    return hexa_void();
}


HexaVal parse_unary(void) {
    HexaVal operand = hexa_void();
    HexaVal k = p_peek_kind();
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("Not"))) || hexa_truthy(hexa_eq(k, hexa_str("Minus"))))) || hexa_truthy(hexa_eq(k, hexa_str("BitNot")))))) {
        HexaVal op_tok = p_advance();
        operand = parse_unary();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("UnaryOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_map_get_ic(op_tok, "value", &__hexa_parser_ic_140)), "left", operand), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Typeof")))) {
        p_advance();
        operand = parse_unary();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("UnaryOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("typeof")), "left", operand), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    return parse_postfix();
    return hexa_void();
}


HexaVal parse_postfix(void) {
    HexaVal field_name = hexa_void();
    HexaVal slice_end = hexa_void();
    HexaVal end = hexa_void();
    HexaVal expr = parse_primary();
    HexaVal cont = hexa_bool(1);
    while (hexa_truthy(cont)) {
        HexaVal k = p_peek_kind();
        if (hexa_truthy(hexa_eq(k, hexa_str("LParen")))) {
            p_advance();
            HexaVal args = parse_args();
            p_expect(hexa_str("RParen"));
            expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Call")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", args), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        } else {
            if (hexa_truthy(hexa_eq(k, hexa_str("Dot")))) {
                p_advance();
                HexaVal next_k = p_peek_kind();
                if (hexa_truthy(hexa_eq(next_k, hexa_str("IntLit")))) {
                    HexaVal idx_tok = p_advance();
                    expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Index")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("IntLit")), "name", hexa_str("")), "value", hexa_index_get(idx_tok, hexa_str("value"))), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""))), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                } else {
                    field_name = p_expect_ident();
                    expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Field")), "name", field_name), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                }
            } else {
                if (hexa_truthy(hexa_eq(k, hexa_str("QuestionDot")))) {
                    p_advance();
                    field_name = p_expect_ident();
                    expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("OptField")), "name", field_name), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                } else {
                    if (hexa_truthy(hexa_eq(k, hexa_str("LBracket")))) {
                        p_advance();
                        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
                            p_advance();
                            slice_end = hexa_str("");
                            if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBracket")))))) {
                                slice_end = parse_expr();
                            }
                            p_expect(hexa_str("RBracket"));
                            expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Slice")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", slice_end), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                        } else {
                            HexaVal index = parse_expr();
                            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
                                p_advance();
                                slice_end = hexa_str("");
                                if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBracket")))))) {
                                    slice_end = parse_expr();
                                }
                                p_expect(hexa_str("RBracket"));
                                expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Slice")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", index), "cond", slice_end), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                            } else {
                                p_expect(hexa_str("RBracket"));
                                expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Index")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", index), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                            }
                        }
                    } else {
                        if (hexa_truthy(hexa_eq(k, hexa_str("DotDot")))) {
                            p_advance();
                            end = parse_addition();
                            HexaVal step_expr = hexa_str("");
                            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Step")))) {
                                p_advance();
                                step_expr = parse_addition();
                            }
                            expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Range")), "name", hexa_str("")), "value", hexa_str("exclusive")), "op", hexa_str("")), "left", expr), "right", end), "cond", step_expr), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                        } else {
                            if (hexa_truthy(hexa_eq(k, hexa_str("DotDotEq")))) {
                                p_advance();
                                end = parse_addition();
                                HexaVal step_expr2 = hexa_str("");
                                if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Step")))) {
                                    p_advance();
                                    step_expr2 = parse_addition();
                                }
                                expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Range")), "name", hexa_str("")), "value", hexa_str("inclusive")), "op", hexa_str("")), "left", expr), "right", end), "cond", step_expr2), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                            } else {
                                if (hexa_truthy(hexa_eq(k, hexa_str("As")))) {
                                    p_advance();
                                    HexaVal type_name = p_expect_ident();
                                    expr = hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BinOp")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("as")), "left", expr), "right", node_ident(type_name)), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                                } else {
                                    cont = hexa_bool(0);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return expr;
    return hexa_void();
}


HexaVal parse_args(void) {
    HexaVal spread_expr = hexa_void();
    HexaVal args = hexa_array_new();
    p_skip_newlines();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen")))) {
        return args;
    }
    p_skip_newlines();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("DotDotDot")))) {
        p_advance();
        spread_expr = parse_expr();
        args = hexa_array_push(args, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Spread")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", spread_expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
    } else {
        args = hexa_array_push(args, parse_expr());
    }
    p_skip_newlines();
    while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
        p_advance();
        p_skip_newlines();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("DotDotDot")))) {
            p_advance();
            spread_expr = parse_expr();
            args = hexa_array_push(args, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Spread")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", spread_expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        } else {
            args = hexa_array_push(args, parse_expr());
        }
        p_skip_newlines();
    }
    p_skip_newlines();
    return args;
    return hexa_void();
}


HexaVal parse_primary(void) {
    HexaVal chars = hexa_void();
    HexaVal first_ch = hexa_void();
    HexaVal items = hexa_void();
    HexaVal lbody = hexa_void();
    HexaVal tok = p_peek();
    HexaVal k = hexa_map_get_ic(tok, "kind", &__hexa_parser_ic_141);
    if (hexa_truthy(hexa_eq(k, hexa_str("IntLit")))) {
        p_advance();
        return node_int_lit(hexa_map_get_ic(tok, "value", &__hexa_parser_ic_142));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("FloatLit")))) {
        p_advance();
        return node_float_lit(hexa_map_get_ic(tok, "value", &__hexa_parser_ic_143));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BoolLit")))) {
        p_advance();
        return node_bool_lit(hexa_map_get_ic(tok, "value", &__hexa_parser_ic_144));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StringLit")))) {
        p_advance();
        return node_string_lit(hexa_map_get_ic(tok, "value", &__hexa_parser_ic_145));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("CharLit")))) {
        p_advance();
        return node_char_lit(hexa_map_get_ic(tok, "value", &__hexa_parser_ic_146));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Ident")))) {
        p_advance();
        HexaVal name = hexa_map_get_ic(tok, "value", &__hexa_parser_ic_147);
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("ColonColon")))) {
            p_advance();
            HexaVal variant = p_expect_ident();
            return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("EnumPath")), "name", name), "value", variant), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        }
        HexaVal type_args = hexa_array_new();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Lt")))) {
            chars = hexa_str_chars(name);
            if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(chars))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                first_ch = hexa_index_get(chars, hexa_int(0));
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool((first_ch.tag==TAG_STR && first_ch.s && isalpha((unsigned char)first_ch.s[0])) || (first_ch.tag==TAG_CHAR && isalpha((unsigned char)first_ch.i)))) && hexa_truthy(hexa_eq(hexa_to_string(first_ch), hexa_str_to_upper(hexa_to_string(first_ch))))))) {
                    type_args = parse_type_params();
                }
            }
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace"))) && hexa_truthy(hexa_bool(!hexa_truthy(p_suppress_struct_lit)))))) {
            chars = hexa_str_chars(name);
            if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(chars))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                first_ch = hexa_index_get(chars, hexa_int(0));
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool((first_ch.tag==TAG_STR && first_ch.s && isalpha((unsigned char)first_ch.s[0])) || (first_ch.tag==TAG_CHAR && isalpha((unsigned char)first_ch.i)))) && hexa_truthy(hexa_eq(hexa_to_string(first_ch), hexa_str_to_upper(hexa_to_string(first_ch))))))) {
                    p_advance();
                    p_skip_newlines();
                    HexaVal fields = hexa_array_new();
                    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
                        HexaVal fname = p_expect_ident();
                        p_expect(hexa_str("Colon"));
                        HexaVal fval = parse_expr();
                        fields = hexa_array_push(fields, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("FieldInit")), "name", fname), "value", hexa_str("")), "op", hexa_str("")), "left", fval), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
                        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                            p_advance();
                        }
                        p_skip_newlines();
                    }
                    p_expect(hexa_str("RBrace"));
                    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("StructInit")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", fields), "items", type_args), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
                }
            }
        }
        return node_ident(name);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("LParen")))) {
        p_advance();
        HexaVal expr = parse_expr();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
            items = hexa_array_push(hexa_array_new(), expr);
            while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                p_advance();
                if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen")))) {
                } else {
                    items = hexa_array_push(items, parse_expr());
                }
            }
            p_expect(hexa_str("RParen"));
            return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Tuple")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", items), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        }
        p_expect(hexa_str("RParen"));
        return expr;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("LBracket")))) {
        p_advance();
        p_skip_newlines();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBracket")))) {
            p_advance();
            return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Array")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_array_new()), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        }
        HexaVal first = parse_expr();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("For")))) {
            p_advance();
            HexaVal comp_var = p_expect_ident();
            HexaVal in_tok = p_advance();
            if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(in_tok, "value", &__hexa_parser_ic_148), hexa_str("in")))))) {
                HexaVal comp_msg = hexa_format_n(hexa_str("expected 'in' after comprehension variable, got '{}'"), hexa_array_push(hexa_array_new(), hexa_map_get_ic(in_tok, "value", &__hexa_parser_ic_149)));
                p_record_error(hexa_map_get_ic(in_tok, "line", &__hexa_parser_ic_150), hexa_map_get_ic(in_tok, "col", &__hexa_parser_ic_151), comp_msg);
                hexa_println(hexa_add(hexa_str("Parse error: "), comp_msg));
            }
            HexaVal comp_iter = parse_expr();
            HexaVal comp_cond = hexa_str("");
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("If")))) {
                p_advance();
                comp_cond = parse_expr();
            }
            p_expect(hexa_str("RBracket"));
            return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ListComp")), "name", comp_var), "value", hexa_str("")), "op", hexa_str("")), "left", first), "right", hexa_str("")), "cond", comp_cond), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", comp_iter), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        }
        items = hexa_array_push(hexa_array_new(), first);
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
            p_advance();
        }
        p_skip_newlines();
        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBracket"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("DotDotDot")))) {
                p_advance();
                HexaVal spread_expr = parse_expr();
                items = hexa_array_push(items, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Spread")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", spread_expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
            } else {
                items = hexa_array_push(items, parse_expr());
            }
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                p_advance();
            }
            p_skip_newlines();
        }
        p_expect(hexa_str("RBracket"));
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Array")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", items), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("HashLBrace")))) {
        p_advance();
        p_skip_newlines();
        items = hexa_array_new();
        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
            HexaVal key_expr = parse_expr();
            p_expect(hexa_str("Colon"));
            HexaVal val_expr = parse_expr();
            items = hexa_array_push(items, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("MapEntry")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", key_expr), "right", val_expr), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                p_advance();
            }
            p_skip_newlines();
        }
        p_expect(hexa_str("RBrace"));
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("MapLit")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", items), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("If")))) {
        return parse_if_expr();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Match")))) {
        return parse_match_expr();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BitOr")))) {
        p_advance();
        HexaVal lparams = hexa_array_new();
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("BitOr")))))) {
            lparams = hexa_array_push(lparams, p_expect_ident());
            while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                p_advance();
                lparams = hexa_array_push(lparams, p_expect_ident());
            }
        }
        p_expect(hexa_str("BitOr"));
        lbody = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace")))) {
            lbody = parse_block();
        } else {
            lbody = parse_expr();
        }
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Lambda")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", lbody), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", lparams), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Or")))) {
        p_advance();
        lbody = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace")))) {
            lbody = parse_block();
        } else {
            lbody = parse_expr();
        }
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Lambda")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", lbody), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_array_new()), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Fn")))) {
        p_advance();
        p_expect(hexa_str("LParen"));
        HexaVal fparams = parse_params();
        p_expect(hexa_str("RParen"));
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
            p_advance();
            HexaVal _ret = parse_type_annotation();
        }
        HexaVal fbody = parse_block();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("Lambda")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", fbody), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", fparams), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    HexaVal msg3 = hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("unexpected token "), hexa_map_get_ic(tok, "kind", &__hexa_parser_ic_152)), hexa_str(" ('")), hexa_map_get_ic(tok, "value", &__hexa_parser_ic_153)), hexa_str("')"));
    p_record_error(hexa_map_get_ic(tok, "line", &__hexa_parser_ic_154), hexa_map_get_ic(tok, "col", &__hexa_parser_ic_155), msg3);
    p_emit_parse_error(tok, msg3);
    p_advance();
    return empty_node();
    return hexa_void();
}


HexaVal parse_try_catch(void) {
    p_advance();
    HexaVal try_body = parse_block();
    p_skip_newlines();
    p_expect(hexa_str("Catch"));
    HexaVal catch_var = hexa_str("_");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
        p_advance();
        catch_var = p_expect_ident();
        p_expect(hexa_str("RParen"));
    } else {
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Ident")))) {
            catch_var = p_expect_ident();
        }
    }
    HexaVal catch_body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("TryCatch")), "name", catch_var), "value", hexa_str("")), "op", hexa_str("")), "left", try_body), "right", catch_body), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_throw_stmt(void) {
    p_advance();
    HexaVal expr = parse_expr();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ThrowStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_panic_stmt(void) {
    p_advance();
    p_expect(hexa_str("LParen"));
    HexaVal msg = parse_expr();
    p_expect(hexa_str("RParen"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("PanicStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", msg), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_recover_stmt(void) {
    p_advance();
    HexaVal catch_var = hexa_str("_");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("BitOr")))) {
        p_advance();
        catch_var = p_expect_ident();
        p_expect(hexa_str("BitOr"));
    }
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("RecoverStmt")), "name", catch_var), "value", hexa_str("")), "op", hexa_str("")), "left", body), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_drop_stmt(void) {
    p_advance();
    p_expect(hexa_str("LParen"));
    HexaVal var_name = p_expect_ident();
    p_expect(hexa_str("RParen"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("DropStmt")), "name", var_name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_spawn_stmt(void) {
    p_advance();
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("SpawnStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_scope_stmt(void) {
    p_advance();
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ScopeStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_select_stmt(void) {
    p_advance();
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal arms = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        HexaVal expr = parse_expr();
        p_expect(hexa_str("Arrow"));
        HexaVal body = parse_block();
        arms = hexa_array_push(arms, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("SelectArm")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("SelectStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", arms), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_async_fn(void) {
    p_advance();
    p_expect(hexa_str("Fn"));
    HexaVal name = p_expect_ident();
    p_expect(hexa_str("LParen"));
    HexaVal params = parse_params();
    p_expect(hexa_str("RParen"));
    HexaVal ret = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
        p_advance();
        ret = parse_type_annotation();
    }
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("AsyncFnDecl")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", params), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", ret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_attribute_prefix(void) {
    HexaVal attr = p_advance();
    HexaVal attr_name = hexa_map_get_ic(attr, "value", &__hexa_parser_ic_156);
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(attr_name, hexa_str("symbol"))) || hexa_truthy(hexa_eq(attr_name, hexa_str("link")))))) {
        p_expect(hexa_str("LParen"));
        HexaVal tok = p_advance();
        HexaVal val = hexa_map_get_ic(tok, "value", &__hexa_parser_ic_157);
        p_expect(hexa_str("RParen"));
        if (hexa_truthy(hexa_eq(attr_name, hexa_str("symbol")))) {
            p_pending_symbol = val;
        } else {
            p_pending_link = val;
        }
        p_skip_newlines();
        return parse_stmt();
    }
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
        p_advance();
        HexaVal depth = hexa_int(1);
        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(depth); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); }))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
                depth = hexa_add(depth, hexa_int(1));
            }
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen")))) {
                depth = hexa_sub(depth, hexa_int(1));
            }
            p_advance();
        }
    }
    p_skip_newlines();
    return parse_stmt();
    return hexa_void();
}


HexaVal parse_extern_fn(void) {
    p_advance();
    p_expect(hexa_str("Fn"));
    HexaVal name = p_expect_ident();
    p_expect(hexa_str("LParen"));
    HexaVal params = parse_params();
    p_expect(hexa_str("RParen"));
    HexaVal ret = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
        p_advance();
        ret = parse_type_annotation();
    }
    HexaVal body = hexa_array_new();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace")))) {
        body = parse_block();
    }
    HexaVal sym = p_pending_symbol;
    HexaVal link = p_pending_link;
    p_pending_symbol = hexa_str("");
    p_pending_link = hexa_str("");
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ExternFnDecl")), "name", name), "value", sym), "op", link), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", params), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", ret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_type_alias(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    p_expect(hexa_str("Eq"));
    HexaVal typ = parse_type_annotation();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("TypeAlias")), "name", name), "value", typ), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_atomic_let(void) {
    p_advance();
    p_expect(hexa_str("Let"));
    HexaVal name = p_expect_ident();
    HexaVal typ = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
        p_advance();
        typ = parse_type_annotation();
    }
    p_expect(hexa_str("Eq"));
    HexaVal expr = parse_expr();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("AtomicLet")), "name", name), "value", typ), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_break_stmt(void) {
    p_advance();
    HexaVal label = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Label")))) {
        label = hexa_map_get_ic(p_advance(), "value", &__hexa_parser_ic_158);
    } else {
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Ident")))) {
            label = hexa_map_get_ic(p_advance(), "value", &__hexa_parser_ic_159);
        }
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BreakStmt")), "name", label), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_continue_stmt(void) {
    p_advance();
    HexaVal label = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Label")))) {
        label = hexa_map_get_ic(p_advance(), "value", &__hexa_parser_ic_160);
    } else {
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Ident")))) {
            label = hexa_map_get_ic(p_advance(), "value", &__hexa_parser_ic_161);
        }
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ContinueStmt")), "name", label), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_do_while_stmt(void) {
    p_advance();
    HexaVal body = parse_block();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("While")))) {
        p_advance();
    } else {
        HexaVal tok = p_peek();
        p_record_error(hexa_map_get_ic(tok, "line", &__hexa_parser_ic_162), hexa_map_get_ic(tok, "col", &__hexa_parser_ic_163), hexa_str("expected 'while' after do block"));
        hexa_println(hexa_str("Parse error: expected 'while' after do block"));
    }
    HexaVal prev_supp = p_suppress_struct_lit;
    p_suppress_struct_lit = hexa_bool(1);
    HexaVal cond = parse_expr();
    p_suppress_struct_lit = prev_supp;
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("DoWhileStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", cond), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_defer_stmt(void) {
    p_advance();
    HexaVal body = hexa_array_new();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace")))) {
        body = parse_block();
    } else {
        HexaVal expr = parse_expr();
        body = hexa_array_push(hexa_array_new(), hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ExprStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("DeferStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_labeled_loop(void) {
    HexaVal tok = hexa_void();
    HexaVal label = hexa_map_get_ic(p_advance(), "value", &__hexa_parser_ic_164);
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
        p_advance();
    } else {
        tok = p_peek();
        p_record_error(hexa_map_get_ic(tok, "line", &__hexa_parser_ic_165), hexa_map_get_ic(tok, "col", &__hexa_parser_ic_166), hexa_str("expected ':' after label"));
        hexa_println(hexa_add(hexa_add(hexa_str("Parse error: expected ':' after label '"), label), hexa_str("'")));
    }
    HexaVal next = p_peek_kind();
    HexaVal loop_node = hexa_str("");
    if (hexa_truthy(hexa_eq(next, hexa_str("For")))) {
        loop_node = parse_for_stmt();
    } else {
        if (hexa_truthy(hexa_eq(next, hexa_str("While")))) {
            loop_node = parse_while_stmt();
        } else {
            if (hexa_truthy(hexa_eq(next, hexa_str("Loop")))) {
                loop_node = parse_loop_stmt();
            } else {
                tok = p_peek();
                p_record_error(hexa_map_get_ic(tok, "line", &__hexa_parser_ic_167), hexa_map_get_ic(tok, "col", &__hexa_parser_ic_168), hexa_str("expected for/while/loop after label"));
                hexa_println(hexa_add(hexa_add(hexa_str("Parse error: expected for/while/loop after label '"), label), hexa_str("'")));
                return empty_node();
            }
        }
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_map_get_ic(loop_node, "kind", &__hexa_parser_ic_169)), "name", hexa_map_get_ic(loop_node, "name", &__hexa_parser_ic_170)), "value", label), "op", hexa_map_get_ic(loop_node, "op", &__hexa_parser_ic_171)), "left", hexa_map_get_ic(loop_node, "left", &__hexa_parser_ic_172)), "right", hexa_map_get_ic(loop_node, "right", &__hexa_parser_ic_173)), "cond", hexa_map_get_ic(loop_node, "cond", &__hexa_parser_ic_174)), "then_body", hexa_map_get_ic(loop_node, "then_body", &__hexa_parser_ic_175)), "else_body", hexa_map_get_ic(loop_node, "else_body", &__hexa_parser_ic_176)), "params", hexa_map_get_ic(loop_node, "params", &__hexa_parser_ic_177)), "body", hexa_map_get_ic(loop_node, "body", &__hexa_parser_ic_178)), "args", hexa_map_get_ic(loop_node, "args", &__hexa_parser_ic_179)), "fields", hexa_map_get_ic(loop_node, "fields", &__hexa_parser_ic_180)), "items", hexa_map_get_ic(loop_node, "items", &__hexa_parser_ic_181)), "variants", hexa_map_get_ic(loop_node, "variants", &__hexa_parser_ic_182)), "arms", hexa_map_get_ic(loop_node, "arms", &__hexa_parser_ic_183)), "iter_expr", hexa_map_get_ic(loop_node, "iter_expr", &__hexa_parser_ic_184)), "ret_type", hexa_map_get_ic(loop_node, "ret_type", &__hexa_parser_ic_185)), "target", hexa_map_get_ic(loop_node, "target", &__hexa_parser_ic_186)), "trait_name", hexa_map_get_ic(loop_node, "trait_name", &__hexa_parser_ic_187)), "methods", hexa_map_get_ic(loop_node, "methods", &__hexa_parser_ic_188));
    return hexa_void();
}


HexaVal parse_yield_stmt(void) {
    p_advance();
    HexaVal expr = hexa_str("");
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Newline"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        expr = parse_expr();
    }
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("YieldStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_comptime_stmt(void) {
    HexaVal name = hexa_void();
    HexaVal body = hexa_void();
    HexaVal typ = hexa_void();
    HexaVal expr = hexa_void();
    p_advance();
    HexaVal next = p_peek_kind();
    if (hexa_truthy(hexa_eq(next, hexa_str("Fn")))) {
        p_advance();
        name = p_expect_ident();
        p_expect(hexa_str("LParen"));
        HexaVal params = parse_params();
        p_expect(hexa_str("RParen"));
        HexaVal ret = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
            p_advance();
            ret = parse_type_annotation();
        }
        body = parse_block();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ComptimeFnDecl")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", params), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", ret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(next, hexa_str("Const")))) {
        p_advance();
        name = p_expect_ident();
        typ = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
            p_advance();
            typ = parse_type_annotation();
        }
        p_expect(hexa_str("Eq"));
        expr = parse_expr();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ComptimeConst")), "name", name), "value", typ), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(next, hexa_str("Let")))) {
        p_advance();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Mut")))) {
            p_advance();
        }
        name = p_expect_ident();
        typ = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
            p_advance();
            typ = parse_type_annotation();
        }
        p_expect(hexa_str("Eq"));
        expr = parse_expr();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ComptimeLet")), "name", name), "value", typ), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(next, hexa_str("Assert")))) {
        p_advance();
        expr = parse_expr();
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ComptimeAssert")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", expr), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("ComptimeBlock")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_intent_stmt(void) {
    p_advance();
    HexaVal desc = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("StringLit")))) {
        desc = hexa_map_get_ic(p_advance(), "value", &__hexa_parser_ic_189);
    } else {
        desc = p_expect_ident();
    }
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal fields = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        HexaVal key = p_expect_ident();
        p_expect(hexa_str("Colon"));
        HexaVal val = parse_expr();
        fields = hexa_array_push(fields, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("IntentField")), "name", key), "value", hexa_str("")), "op", hexa_str("")), "left", val), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
            p_advance();
        }
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("IntentStmt")), "name", desc), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", fields), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_verify_stmt(void) {
    p_advance();
    HexaVal name = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("StringLit")))) {
        name = hexa_map_get_ic(p_advance(), "value", &__hexa_parser_ic_190);
    } else {
        name = p_expect_ident();
    }
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("VerifyStmt")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_generate_stmt(void) {
    HexaVal desc = hexa_void();
    p_advance();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Fn")))) {
        p_advance();
        HexaVal name = p_expect_ident();
        p_expect(hexa_str("LParen"));
        HexaVal params = parse_params();
        p_expect(hexa_str("RParen"));
        HexaVal ret = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
            p_advance();
            ret = parse_type_annotation();
        }
        p_expect(hexa_str("LBrace"));
        p_skip_newlines();
        desc = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("StringLit")))) {
            desc = hexa_map_get_ic(p_advance(), "value", &__hexa_parser_ic_191);
        }
        p_skip_newlines();
        p_expect(hexa_str("RBrace"));
        return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("GenerateFnStmt")), "name", name), "value", desc), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", params), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", ret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    }
    HexaVal type_hint = hexa_str("");
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LBrace")))))) {
        type_hint = p_expect_ident();
    }
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    desc = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("StringLit")))) {
        desc = hexa_map_get_ic(p_advance(), "value", &__hexa_parser_ic_192);
    }
    p_skip_newlines();
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("GenerateStmt")), "name", type_hint), "value", desc), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_optimize_stmt(void) {
    p_advance();
    p_expect(hexa_str("Fn"));
    HexaVal name = p_expect_ident();
    p_expect(hexa_str("LParen"));
    HexaVal params = parse_params();
    p_expect(hexa_str("RParen"));
    HexaVal ret = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
        p_advance();
        ret = parse_type_annotation();
    }
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("OptimizeFnStmt")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", params), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", ret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_effect_decl(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    HexaVal tparams = hexa_array_new();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Lt")))) {
        tparams = parse_type_params();
    }
    p_skip_newlines();
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal ops = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        p_expect(hexa_str("Fn"));
        HexaVal op_name = p_expect_ident();
        p_expect(hexa_str("LParen"));
        HexaVal op_params = parse_params();
        p_expect(hexa_str("RParen"));
        HexaVal op_ret = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
            p_advance();
            op_ret = parse_type_annotation();
        }
        ops = hexa_array_push(ops, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("EffectOp")), "name", op_name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", op_params), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", op_ret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("EffectDecl")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", tparams), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", ops), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_pure_fn(void) {
    p_advance();
    p_expect(hexa_str("Fn"));
    HexaVal name = p_expect_ident();
    p_expect(hexa_str("LParen"));
    HexaVal params = parse_params();
    p_expect(hexa_str("RParen"));
    HexaVal ret = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Arrow")))) {
        p_advance();
        ret = parse_type_annotation();
    }
    HexaVal body = parse_block();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("PureFnDecl")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", params), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", ret), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_macro_def(void) {
    p_advance();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Not")))) {
        p_advance();
    }
    HexaVal name = p_expect_ident();
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal rules = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        p_expect(hexa_str("LParen"));
        p_skip_newlines();
        HexaVal pat_tokens = hexa_array_new();
        while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
            HexaVal tok = p_advance();
            pat_tokens = hexa_array_push(pat_tokens, hexa_map_get_ic(tok, "value", &__hexa_parser_ic_193));
            p_skip_newlines();
        }
        p_expect(hexa_str("RParen"));
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eq")))) {
            p_advance();
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Gt")))) {
                p_advance();
            }
        }
        HexaVal body = parse_block();
        rules = hexa_array_push(rules, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("MacroRule")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", pat_tokens), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma"))) || hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Semicolon")))))) {
            p_advance();
        }
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("MacroDef")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", rules), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_derive_decl(void) {
    p_advance();
    p_expect(hexa_str("LParen"));
    HexaVal traits = hexa_array_new();
    traits = hexa_array_push(traits, p_expect_ident());
    while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
        p_advance();
        traits = hexa_array_push(traits, p_expect_ident());
    }
    p_expect(hexa_str("RParen"));
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("For")))) {
        p_advance();
    } else {
        p_expect_ident();
    }
    HexaVal type_name = p_expect_ident();
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("DeriveDecl")), "name", type_name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", traits), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_theorem_stmt(void) {
    p_advance();
    HexaVal name = p_expect_ident();
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal stmts = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        stmts = hexa_array_push(stmts, parse_stmt());
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("TheoremStmt")), "name", name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", stmts), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_handle_stmt(void) {
    p_advance();
    HexaVal body = parse_block();
    p_skip_newlines();
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("With")))) {
        p_advance();
    } else {
        p_expect_ident();
    }
    p_skip_newlines();
    p_expect(hexa_str("LBrace"));
    p_skip_newlines();
    HexaVal handlers = hexa_array_new();
    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RBrace"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
        HexaVal effect_name = p_expect_ident();
        p_expect(hexa_str("Dot"));
        HexaVal op_name = p_expect_ident();
        HexaVal hparams = hexa_array_new();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
            p_advance();
            while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("RParen"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Eof")))))))) {
                hparams = hexa_array_push(hparams, p_expect_ident());
                if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
                    p_advance();
                }
            }
            p_expect(hexa_str("RParen"));
        }
        HexaVal pk = p_peek_kind();
        if (hexa_truthy(hexa_eq(pk, hexa_str("Eq")))) {
            p_advance();
            if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Gt")))) {
                p_advance();
            }
        } else {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(pk, hexa_str("Arrow"))) || hexa_truthy(hexa_eq(pk, hexa_str("FatArrow")))))) {
                p_advance();
            }
        }
        HexaVal hbody = parse_block();
        handlers = hexa_array_push(handlers, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("EffectHandler")), "name", op_name), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hparams), "body", hbody), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", effect_name), "trait_name", hexa_str("")), "methods", hexa_str("")));
        p_skip_newlines();
    }
    p_expect(hexa_str("RBrace"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("HandleWithStmt")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", body), "args", hexa_str("")), "fields", hexa_str("")), "items", handlers), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal parse_visibility(void) {
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Pub")))) {
        p_advance();
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("LParen")))) {
            p_advance();
            HexaVal vis_scope = p_expect_ident();
            p_expect(hexa_str("RParen"));
            return vis_scope;
        }
        return hexa_str("pub");
    }
    return hexa_str("private");
    return hexa_void();
}


HexaVal parse_type_params(void) {
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Lt")))))) {
        return hexa_array_new();
    }
    p_advance();
    HexaVal tparams = hexa_array_new();
    HexaVal name = p_expect_ident();
    HexaVal bound = hexa_str("");
    if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
        p_advance();
        bound = parse_type_annotation();
    }
    tparams = hexa_array_push(tparams, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("TypeParam")), "name", name), "value", bound), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
    while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
        p_advance();
        HexaVal pname = p_expect_ident();
        HexaVal pbound = hexa_str("");
        if (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Colon")))) {
            p_advance();
            pbound = parse_type_annotation();
        }
        tparams = hexa_array_push(tparams, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("TypeParam")), "name", pname), "value", pbound), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
    }
    p_expect(hexa_str("Gt"));
    return tparams;
    return hexa_void();
}


HexaVal parse_where_clauses(void) {
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Where")))))) {
        return hexa_array_new();
    }
    p_advance();
    HexaVal clauses = hexa_array_new();
    HexaVal tname = p_expect_ident();
    p_expect(hexa_str("Colon"));
    HexaVal tbound = parse_type_annotation();
    clauses = hexa_array_push(clauses, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("WhereClause")), "name", tname), "value", tbound), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
    while (hexa_truthy(hexa_eq(p_peek_kind(), hexa_str("Comma")))) {
        p_advance();
        HexaVal wname = p_expect_ident();
        p_expect(hexa_str("Colon"));
        HexaVal wbound = parse_type_annotation();
        clauses = hexa_array_push(clauses, hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("WhereClause")), "name", wname), "value", wbound), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str("")));
    }
    return clauses;
    return hexa_void();
}


HexaVal ast_to_string(HexaVal node, HexaVal indent) {
    HexaVal l = hexa_void();
    HexaVal r = hexa_void();
    HexaVal obj = hexa_void();
    HexaVal v = hexa_void();
    HexaVal names = hexa_void();
    HexaVal pad = hexa_str("");
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(indent); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        pad = hexa_add(pad, hexa_str("  "));
        i = hexa_add(i, hexa_int(1));
    }
    HexaVal k = hexa_map_get_ic(node, "kind", &__hexa_parser_ic_194);
    if (hexa_truthy(hexa_eq(k, hexa_str("IntLit")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("IntLit(")), hexa_map_get_ic(node, "value", &__hexa_parser_ic_195)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("FloatLit")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("FloatLit(")), hexa_map_get_ic(node, "value", &__hexa_parser_ic_196)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BoolLit")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("BoolLit(")), hexa_map_get_ic(node, "value", &__hexa_parser_ic_197)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StringLit")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("StringLit(\"")), hexa_map_get_ic(node, "value", &__hexa_parser_ic_198)), hexa_str("\")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("CharLit")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("CharLit('")), hexa_map_get_ic(node, "value", &__hexa_parser_ic_199)), hexa_str("')"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Ident")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("Ident(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_200)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Wildcard")))) {
        return hexa_add(pad, hexa_str("Wildcard"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BinOp")))) {
        l = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_201), hexa_int(0));
        r = ast_to_string(hexa_map_get_ic(node, "right", &__hexa_parser_ic_202), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("BinOp(")), hexa_map_get_ic(node, "op", &__hexa_parser_ic_203)), hexa_str(", ")), l), hexa_str(", ")), r), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("UnaryOp")))) {
        HexaVal operand = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_204), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("UnaryOp(")), hexa_map_get_ic(node, "op", &__hexa_parser_ic_205)), hexa_str(", ")), operand), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Call")))) {
        HexaVal callee = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_206), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("Call(")), callee), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_parser_ic_207))))), hexa_str(" args])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Field")))) {
        obj = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_208), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("Field(")), obj), hexa_str(".")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_209)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("OptField")))) {
        obj = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_210), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("OptField(")), obj), hexa_str("?.")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_211)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Index")))) {
        obj = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_212), hexa_int(0));
        HexaVal idx = ast_to_string(hexa_map_get_ic(node, "right", &__hexa_parser_ic_213), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("Index(")), obj), hexa_str("[")), idx), hexa_str("])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("IfExpr")))) {
        HexaVal c = ast_to_string(hexa_map_get_ic(node, "cond", &__hexa_parser_ic_214), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("IfExpr(")), c), hexa_str(", then=[")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "then_body", &__hexa_parser_ic_215))))), hexa_str("], else=[")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "else_body", &__hexa_parser_ic_216))))), hexa_str("])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("IfLetExpr")))) {
        HexaVal p = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_217), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("IfLetExpr(")), p), hexa_str(", then=[")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "then_body", &__hexa_parser_ic_218))))), hexa_str("], else=[")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "else_body", &__hexa_parser_ic_219))))), hexa_str("])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("MatchExpr")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("MatchExpr([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "arms", &__hexa_parser_ic_220))))), hexa_str(" arms])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Array")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("Array([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_parser_ic_221))))), hexa_str(" items])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ListComp")))) {
        HexaVal body_s = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_222), hexa_int(0));
        HexaVal iter_s = ast_to_string(hexa_map_get_ic(node, "iter_expr", &__hexa_parser_ic_223), hexa_int(0));
        HexaVal filt = hexa_str("");
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "cond", &__hexa_parser_ic_224)), hexa_str("string")))))) {
            filt = hexa_add(hexa_str(" if "), ast_to_string(hexa_map_get_ic(node, "cond", &__hexa_parser_ic_225), hexa_int(0)));
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("ListComp(")), body_s), hexa_str(" for ")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_226)), hexa_str(" in ")), iter_s), filt), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StructInit")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("StructInit(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_227)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_parser_ic_228))))), hexa_str(" fields])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Slice")))) {
        obj = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_229), hexa_int(0));
        HexaVal s_str = hexa_str("");
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "right", &__hexa_parser_ic_230), hexa_str("")))))) {
            s_str = ast_to_string(hexa_map_get_ic(node, "right", &__hexa_parser_ic_231), hexa_int(0));
        }
        HexaVal e_str = hexa_str("");
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "cond", &__hexa_parser_ic_232), hexa_str("")))))) {
            e_str = ast_to_string(hexa_map_get_ic(node, "cond", &__hexa_parser_ic_233), hexa_int(0));
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("Slice(")), obj), hexa_str("[")), s_str), hexa_str(":")), e_str), hexa_str("])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Range")))) {
        HexaVal s = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_234), hexa_int(0));
        HexaVal e = ast_to_string(hexa_map_get_ic(node, "right", &__hexa_parser_ic_235), hexa_int(0));
        HexaVal step_str = hexa_str("");
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "cond", &__hexa_parser_ic_236), hexa_str("")))))) {
            step_str = hexa_add(hexa_str(" step "), ast_to_string(hexa_map_get_ic(node, "cond", &__hexa_parser_ic_237), hexa_int(0)));
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("Range(")), s), hexa_str("..")), e), hexa_str(", ")), hexa_map_get_ic(node, "value", &__hexa_parser_ic_238)), step_str), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("EnumPath")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("EnumPath(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_239)), hexa_str("::")), hexa_map_get_ic(node, "value", &__hexa_parser_ic_240)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Lambda")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("Lambda([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_parser_ic_241))))), hexa_str(" params])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Tuple")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("Tuple([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_parser_ic_242))))), hexa_str(" items])"));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("LetStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("LetMutStmt")))))) {
        v = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_243), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, k), hexa_str("(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_244)), hexa_str(" = ")), v), hexa_str(")"));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("ConstStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("StaticStmt")))))) {
        v = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_245), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, k), hexa_str("(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_246)), hexa_str(" = ")), v), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ReturnStmt")))) {
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(node, "left", &__hexa_parser_ic_247), hexa_str("")))) {
            return hexa_add(pad, hexa_str("ReturnStmt()"));
        }
        v = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_248), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("ReturnStmt(")), v), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("FnDecl")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("FnDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_249)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_parser_ic_250))))), hexa_str(" params], [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_251))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StructDecl")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("StructDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_252)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_parser_ic_253))))), hexa_str(" fields])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("EnumDecl")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("EnumDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_254)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "variants", &__hexa_parser_ic_255))))), hexa_str(" variants])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ForStmt")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("ForStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_256)), hexa_str(" in ..., [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_257))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("WhileStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("WhileStmt(..., [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_258))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("LoopStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("LoopStmt([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_259))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ExprStmt")))) {
        v = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_260), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("ExprStmt(")), v), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("AssignStmt")))) {
        l = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_261), hexa_int(0));
        r = ast_to_string(hexa_map_get_ic(node, "right", &__hexa_parser_ic_262), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("AssignStmt(")), l), hexa_str(" = ")), r), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("AssertStmt")))) {
        v = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_263), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("AssertStmt(")), v), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ProofStmt")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("ProofStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_264)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_265))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ImplBlock")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("ImplBlock(")), hexa_map_get_ic(node, "target", &__hexa_parser_ic_266)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "methods", &__hexa_parser_ic_267))))), hexa_str(" methods])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("TraitDecl")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("TraitDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_268)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "methods", &__hexa_parser_ic_269))))), hexa_str(" methods])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("UseStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("UseStmt([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_parser_ic_270))))), hexa_str(" segments])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ModStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("ModStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_271)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BreakStmt")))) {
        return hexa_add(pad, hexa_str("BreakStmt"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ContinueStmt")))) {
        return hexa_add(pad, hexa_str("ContinueStmt"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("YieldStmt")))) {
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(node, "left", &__hexa_parser_ic_272), hexa_str("")))) {
            return hexa_add(pad, hexa_str("YieldStmt()"));
        }
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("YieldStmt(")), ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_273), hexa_int(0))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ComptimeFnDecl")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("ComptimeFnDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_274)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_parser_ic_275))))), hexa_str(" params])"));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("ComptimeConst"))) || hexa_truthy(hexa_eq(k, hexa_str("ComptimeLet")))))) {
        v = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_276), hexa_int(0));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, k), hexa_str("(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_277)), hexa_str(" = ")), v), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ComptimeBlock")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("ComptimeBlock([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_278))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ComptimeAssert")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("ComptimeAssert(")), ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_279), hexa_int(0))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("IntentStmt")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("IntentStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_280)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_parser_ic_281))))), hexa_str(" fields])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("VerifyStmt")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("VerifyStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_282)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_283))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("GenerateFnStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("GenerateStmt")))))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(pad, k), hexa_str("(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_284)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("OptimizeFnStmt")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("OptimizeFnStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_285)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_parser_ic_286))))), hexa_str(" params])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("EffectDecl")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("EffectDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_287)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_parser_ic_288))))), hexa_str(" ops])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("PureFnDecl")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("PureFnDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_289)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_parser_ic_290))))), hexa_str(" params])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("MacroDef")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("MacroDef(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_291)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_parser_ic_292))))), hexa_str(" rules])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("DeriveDecl")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("DeriveDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_293)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_parser_ic_294))))), hexa_str(" traits])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("TheoremStmt")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("TheoremStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_295)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_296))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("HandleWithStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("HandleWithStmt([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_parser_ic_297))))), hexa_str(" handlers])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("GuardStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("GuardStmt(cond, [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "else_body", &__hexa_parser_ic_298))))), hexa_str(" else stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("GuardLetStmt")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("GuardLetStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_299)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "else_body", &__hexa_parser_ic_300))))), hexa_str(" else stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("WithStmt")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("WithStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_301)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_302))))), hexa_str(" body stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("WalrusExpr")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("WalrusExpr(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_303)), hexa_str(", ")), ast_to_string(hexa_map_get_ic(node, "right", &__hexa_parser_ic_304), hexa_int(0))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("TryCatch")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("TryCatch(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_305)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ThrowStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("ThrowStmt(")), ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_306), hexa_int(0))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("PanicStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("PanicStmt(")), ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_307), hexa_int(0))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("DropStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("DropStmt(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_308)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("SpawnStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("SpawnStmt([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_309))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ScopeStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("ScopeStmt([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_parser_ic_310))))), hexa_str(" stmts])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("SelectStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("SelectStmt([")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "arms", &__hexa_parser_ic_311))))), hexa_str(" arms])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("AsyncFnDecl")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("AsyncFnDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_312)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_parser_ic_313))))), hexa_str(" params])"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ExternFnDecl")))) {
        HexaVal sym_info = hexa_str("");
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "value", &__hexa_parser_ic_314), hexa_str("")))))) {
            sym_info = hexa_add(hexa_add(hexa_str(", @symbol(\""), hexa_map_get_ic(node, "value", &__hexa_parser_ic_315)), hexa_str("\")"));
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("ExternFnDecl(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_316)), hexa_str(", [")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_parser_ic_317))))), hexa_str(" params]")), sym_info), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("TypeAlias")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("TypeAlias(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_318)), hexa_str(" = ")), hexa_map_get_ic(node, "value", &__hexa_parser_ic_319)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("AtomicLet")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("AtomicLet(")), hexa_map_get_ic(node, "name", &__hexa_parser_ic_320)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("DestructLetStmt")))) {
        v = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_321), hexa_int(0));
        HexaVal rest = hexa_map_get_ic(node, "name", &__hexa_parser_ic_322);
        names = hexa_str_join(hexa_map_get_ic(node, "params", &__hexa_parser_ic_323), hexa_str(", "));
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(rest, hexa_str("")))))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("DestructLetStmt([")), names), hexa_str(", ...")), rest), hexa_str("] = ")), v), hexa_str(")"));
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("DestructLetStmt([")), names), hexa_str("] = ")), v), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("MapDestructLetStmt")))) {
        v = ast_to_string(hexa_map_get_ic(node, "left", &__hexa_parser_ic_324), hexa_int(0));
        names = hexa_str_join(hexa_map_get_ic(node, "params", &__hexa_parser_ic_325), hexa_str(", "));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("MapDestructLetStmt({")), names), hexa_str("} = ")), v), hexa_str(")"));
    }
    return hexa_add(hexa_add(hexa_add(pad, hexa_str("Unknown(")), k), hexa_str(")"));
    return hexa_void();
}


HexaVal print_ast(HexaVal stmts) {
    {
        HexaVal __iter_arr = stmts;
        for (int __fi = 0; __fi < hexa_len(__iter_arr); __fi++) {
            HexaVal s = hexa_iter_get(__iter_arr, __fi);
            hexa_println(ast_to_string(s, hexa_int(0)));
        }
    }
    return hexa_void();
}


int _parser_init(int argc, char** argv) {
    hexa_set_args(argc, argv);
    p_tokens = hexa_array_new();
    p_pos = hexa_int(0);
    p_pending_symbol = hexa_str("");
    p_pending_link = hexa_str("");
    p_pending_attrs = hexa_str("");
    p_pending_contract_requires = hexa_str("");
    p_pending_contract_ensures = hexa_str("");
    p_pending_contract_req_text = hexa_str("");
    p_pending_contract_ens_text = hexa_str("");
    p_suppress_struct_lit = hexa_bool(0);
    p_errors = hexa_array_new();
    p_max_errors = hexa_int(50);
    p_last_err_key = hexa_str("");
    return 0;
}

// === type_checker ===


HexaVal annotation_to_type(HexaVal ann);
HexaVal tc_check_stmts(HexaVal stmts);

HexaVal tc_errors;
HexaVal scope_names;
HexaVal scope_types;
HexaVal scope_depths;
HexaVal tc_depth;
HexaVal fn_names;
HexaVal fn_arities;
HexaVal fn_ret_types;
HexaVal fn_cache;
HexaVal scope_cache;
HexaVal struct_names;
HexaVal struct_field_counts;
HexaVal struct_field_offsets;
HexaVal struct_all_field_names;
HexaVal struct_all_field_types;
HexaVal enum_names;
HexaVal enum_variant_counts;
HexaVal enum_variant_offsets;
HexaVal enum_all_variant_names;
HexaVal current_fn_ret_type;
HexaVal current_fn_name;
HexaVal generic_struct_names;
HexaVal generic_struct_param_counts;
HexaVal generic_struct_param_offsets;
HexaVal generic_all_param_names;
HexaVal generic_all_param_bounds;
HexaVal generic_fn_names;
HexaVal generic_fn_param_counts;
HexaVal generic_fn_param_offsets;
HexaVal generic_fn_all_param_names;
HexaVal generic_fn_all_param_bounds;
HexaVal tparam_names;
HexaVal tparam_bound;
HexaVal test_pass;
HexaVal s1;
HexaVal errs1;
HexaVal p2;
HexaVal body2;
HexaVal fd2;
HexaVal args2a;
HexaVal s2a;
HexaVal errs2a;
HexaVal args2b;
HexaVal s2b;
HexaVal errs2b;
HexaVal sf3;
HexaVal sd3;
HexaVal fi3;
HexaVal lp3;
HexaVal fn3a;
HexaVal es3a;
HexaVal s3a;
HexaVal errs3a;
HexaVal fn3b;
HexaVal es3b;
HexaVal s3b;
HexaVal errs3b;
HexaVal body4;
HexaVal s4;
HexaVal errs4;
HexaVal ev5;
HexaVal ed5;
HexaVal lc5;
HexaVal ab5a;
HexaVal arms5a;
HexaVal s5a;
HexaVal errs5a;
HexaVal w5a;
HexaVal ab5b;
HexaVal arms5b;
HexaVal s5b;
HexaVal errs5b;
HexaVal w5b;
HexaVal s6;
HexaVal errs6;
HexaVal fi7;
HexaVal s7;
HexaVal errs7;
HexaVal body8;
HexaVal s8;
HexaVal errs8;
HexaVal fi9;
HexaVal s9;
HexaVal errs9;
HexaVal inner_body;
HexaVal outer_body;
HexaVal s10;
HexaVal errs10;

static HexaIC __hexa_type_checker_ic_0 = {0};
static HexaIC __hexa_type_checker_ic_1 = {0};
static HexaIC __hexa_type_checker_ic_2 = {0};
static HexaIC __hexa_type_checker_ic_3 = {0};
static HexaIC __hexa_type_checker_ic_4 = {0};
static HexaIC __hexa_type_checker_ic_5 = {0};
static HexaIC __hexa_type_checker_ic_6 = {0};
static HexaIC __hexa_type_checker_ic_7 = {0};
static HexaIC __hexa_type_checker_ic_8 = {0};
static HexaIC __hexa_type_checker_ic_9 = {0};
static HexaIC __hexa_type_checker_ic_10 = {0};
static HexaIC __hexa_type_checker_ic_11 = {0};
static HexaIC __hexa_type_checker_ic_12 = {0};
static HexaIC __hexa_type_checker_ic_13 = {0};
static HexaIC __hexa_type_checker_ic_14 = {0};
static HexaIC __hexa_type_checker_ic_15 = {0};
static HexaIC __hexa_type_checker_ic_16 = {0};
static HexaIC __hexa_type_checker_ic_17 = {0};
static HexaIC __hexa_type_checker_ic_18 = {0};
static HexaIC __hexa_type_checker_ic_19 = {0};
static HexaIC __hexa_type_checker_ic_20 = {0};
static HexaIC __hexa_type_checker_ic_21 = {0};
static HexaIC __hexa_type_checker_ic_22 = {0};
static HexaIC __hexa_type_checker_ic_23 = {0};
static HexaIC __hexa_type_checker_ic_24 = {0};
static HexaIC __hexa_type_checker_ic_25 = {0};
static HexaIC __hexa_type_checker_ic_26 = {0};
static HexaIC __hexa_type_checker_ic_27 = {0};
static HexaIC __hexa_type_checker_ic_28 = {0};
static HexaIC __hexa_type_checker_ic_29 = {0};
static HexaIC __hexa_type_checker_ic_30 = {0};
static HexaIC __hexa_type_checker_ic_31 = {0};
static HexaIC __hexa_type_checker_ic_32 = {0};
static HexaIC __hexa_type_checker_ic_33 = {0};
static HexaIC __hexa_type_checker_ic_34 = {0};
static HexaIC __hexa_type_checker_ic_35 = {0};
static HexaIC __hexa_type_checker_ic_36 = {0};
static HexaIC __hexa_type_checker_ic_37 = {0};
static HexaIC __hexa_type_checker_ic_38 = {0};
static HexaIC __hexa_type_checker_ic_39 = {0};
static HexaIC __hexa_type_checker_ic_40 = {0};
static HexaIC __hexa_type_checker_ic_41 = {0};
static HexaIC __hexa_type_checker_ic_42 = {0};
static HexaIC __hexa_type_checker_ic_43 = {0};
static HexaIC __hexa_type_checker_ic_44 = {0};
static HexaIC __hexa_type_checker_ic_45 = {0};
static HexaIC __hexa_type_checker_ic_46 = {0};
static HexaIC __hexa_type_checker_ic_47 = {0};
static HexaIC __hexa_type_checker_ic_48 = {0};
static HexaIC __hexa_type_checker_ic_49 = {0};
static HexaIC __hexa_type_checker_ic_50 = {0};
static HexaIC __hexa_type_checker_ic_51 = {0};
static HexaIC __hexa_type_checker_ic_52 = {0};
static HexaIC __hexa_type_checker_ic_53 = {0};
static HexaIC __hexa_type_checker_ic_54 = {0};
static HexaIC __hexa_type_checker_ic_55 = {0};
static HexaIC __hexa_type_checker_ic_56 = {0};
static HexaIC __hexa_type_checker_ic_57 = {0};
static HexaIC __hexa_type_checker_ic_58 = {0};
static HexaIC __hexa_type_checker_ic_59 = {0};
static HexaIC __hexa_type_checker_ic_60 = {0};
static HexaIC __hexa_type_checker_ic_61 = {0};
static HexaIC __hexa_type_checker_ic_62 = {0};
static HexaIC __hexa_type_checker_ic_63 = {0};
static HexaIC __hexa_type_checker_ic_64 = {0};
static HexaIC __hexa_type_checker_ic_65 = {0};
static HexaIC __hexa_type_checker_ic_66 = {0};
static HexaIC __hexa_type_checker_ic_67 = {0};
static HexaIC __hexa_type_checker_ic_68 = {0};
static HexaIC __hexa_type_checker_ic_69 = {0};
static HexaIC __hexa_type_checker_ic_70 = {0};
static HexaIC __hexa_type_checker_ic_71 = {0};
static HexaIC __hexa_type_checker_ic_72 = {0};
static HexaIC __hexa_type_checker_ic_73 = {0};
static HexaIC __hexa_type_checker_ic_74 = {0};
static HexaIC __hexa_type_checker_ic_75 = {0};
static HexaIC __hexa_type_checker_ic_76 = {0};
static HexaIC __hexa_type_checker_ic_77 = {0};
static HexaIC __hexa_type_checker_ic_78 = {0};
static HexaIC __hexa_type_checker_ic_79 = {0};
static HexaIC __hexa_type_checker_ic_80 = {0};
static HexaIC __hexa_type_checker_ic_81 = {0};
static HexaIC __hexa_type_checker_ic_82 = {0};
static HexaIC __hexa_type_checker_ic_83 = {0};
static HexaIC __hexa_type_checker_ic_84 = {0};
static HexaIC __hexa_type_checker_ic_85 = {0};
static HexaIC __hexa_type_checker_ic_86 = {0};
static HexaIC __hexa_type_checker_ic_87 = {0};
static HexaIC __hexa_type_checker_ic_88 = {0};
static HexaIC __hexa_type_checker_ic_89 = {0};
static HexaIC __hexa_type_checker_ic_90 = {0};
static HexaIC __hexa_type_checker_ic_91 = {0};
static HexaIC __hexa_type_checker_ic_92 = {0};
static HexaIC __hexa_type_checker_ic_93 = {0};
static HexaIC __hexa_type_checker_ic_94 = {0};
static HexaIC __hexa_type_checker_ic_95 = {0};
static HexaIC __hexa_type_checker_ic_96 = {0};
static HexaIC __hexa_type_checker_ic_97 = {0};
static HexaIC __hexa_type_checker_ic_98 = {0};
static HexaIC __hexa_type_checker_ic_99 = {0};
static HexaIC __hexa_type_checker_ic_100 = {0};
static HexaIC __hexa_type_checker_ic_101 = {0};
static HexaIC __hexa_type_checker_ic_102 = {0};
static HexaIC __hexa_type_checker_ic_103 = {0};
static HexaIC __hexa_type_checker_ic_104 = {0};
static HexaIC __hexa_type_checker_ic_105 = {0};
static HexaIC __hexa_type_checker_ic_106 = {0};
static HexaIC __hexa_type_checker_ic_107 = {0};
static HexaIC __hexa_type_checker_ic_108 = {0};
static HexaIC __hexa_type_checker_ic_109 = {0};
static HexaIC __hexa_type_checker_ic_110 = {0};
static HexaIC __hexa_type_checker_ic_111 = {0};
static HexaIC __hexa_type_checker_ic_112 = {0};
static HexaIC __hexa_type_checker_ic_113 = {0};
static HexaIC __hexa_type_checker_ic_114 = {0};
static HexaIC __hexa_type_checker_ic_115 = {0};
static HexaIC __hexa_type_checker_ic_116 = {0};
static HexaIC __hexa_type_checker_ic_117 = {0};
static HexaIC __hexa_type_checker_ic_118 = {0};
static HexaIC __hexa_type_checker_ic_119 = {0};
static HexaIC __hexa_type_checker_ic_120 = {0};
static HexaIC __hexa_type_checker_ic_121 = {0};
static HexaIC __hexa_type_checker_ic_122 = {0};
static HexaIC __hexa_type_checker_ic_123 = {0};
static HexaIC __hexa_type_checker_ic_124 = {0};
static HexaIC __hexa_type_checker_ic_125 = {0};
static HexaIC __hexa_type_checker_ic_126 = {0};
static HexaIC __hexa_type_checker_ic_127 = {0};
static HexaIC __hexa_type_checker_ic_128 = {0};
static HexaIC __hexa_type_checker_ic_129 = {0};
static HexaIC __hexa_type_checker_ic_130 = {0};
static HexaIC __hexa_type_checker_ic_131 = {0};
static HexaIC __hexa_type_checker_ic_132 = {0};
static HexaIC __hexa_type_checker_ic_133 = {0};
static HexaIC __hexa_type_checker_ic_134 = {0};
static HexaIC __hexa_type_checker_ic_135 = {0};
static HexaIC __hexa_type_checker_ic_136 = {0};
static HexaIC __hexa_type_checker_ic_137 = {0};
static HexaIC __hexa_type_checker_ic_138 = {0};
static HexaIC __hexa_type_checker_ic_139 = {0};
static HexaIC __hexa_type_checker_ic_140 = {0};
static HexaIC __hexa_type_checker_ic_141 = {0};
static HexaIC __hexa_type_checker_ic_142 = {0};
static HexaIC __hexa_type_checker_ic_143 = {0};
static HexaIC __hexa_type_checker_ic_144 = {0};
static HexaIC __hexa_type_checker_ic_145 = {0};
static HexaIC __hexa_type_checker_ic_146 = {0};
static HexaIC __hexa_type_checker_ic_147 = {0};
static HexaIC __hexa_type_checker_ic_148 = {0};
static HexaIC __hexa_type_checker_ic_149 = {0};
static HexaIC __hexa_type_checker_ic_150 = {0};
static HexaIC __hexa_type_checker_ic_151 = {0};
static HexaIC __hexa_type_checker_ic_152 = {0};
static HexaIC __hexa_type_checker_ic_153 = {0};
static HexaIC __hexa_type_checker_ic_154 = {0};
static HexaIC __hexa_type_checker_ic_155 = {0};

HexaVal AstNode(HexaVal kind, HexaVal name, HexaVal value, HexaVal op, HexaVal left, HexaVal right, HexaVal cond, HexaVal then_body, HexaVal else_body, HexaVal params, HexaVal body, HexaVal args, HexaVal fields, HexaVal items, HexaVal variants, HexaVal arms, HexaVal iter_expr, HexaVal ret_type, HexaVal target, HexaVal trait_name, HexaVal methods) {
    static const char* const _k[] = {"kind", "name", "value", "op", "left", "right", "cond", "then_body", "else_body", "params", "body", "args", "fields", "items", "variants", "arms", "iter_expr", "ret_type", "target", "trait_name", "methods"};
    HexaVal _v[] = {kind, name, value, op, left, right, cond, then_body, else_body, params, body, args, fields, items, variants, arms, iter_expr, ret_type, target, trait_name, methods};
    return hexa_struct_pack_map("AstNode", 21, _k, _v);
}


HexaVal TypeError(HexaVal message, HexaVal name) {
    static const char* const _k[] = {"message", "name"};
    HexaVal _v[] = {message, name};
    return hexa_struct_pack_map("TypeError", 2, _k, _v);
}


HexaVal tc_error(HexaVal msg) {
    tc_errors = hexa_array_push(tc_errors, TypeError(msg, hexa_str("")));
    return hexa_void();
}


HexaVal tc_error_at(HexaVal name, HexaVal msg) {
    tc_errors = hexa_array_push(tc_errors, TypeError(msg, name));
    return hexa_void();
}


HexaVal TypeErrorEx(HexaVal message, HexaVal name, HexaVal severity) {
    static const char* const _k[] = {"message", "name", "severity"};
    HexaVal _v[] = {message, name, severity};
    return hexa_struct_pack_map("TypeErrorEx", 3, _k, _v);
}


HexaVal tc_push_scope(void) {
    tc_depth = hexa_add(tc_depth, hexa_int(1));
    return hexa_void();
}


HexaVal tc_scope_hash(HexaVal name) {
    HexaVal h = hexa_int(0);
    HexaVal i = hexa_int(0);
    HexaVal n = hexa_int(hexa_len(name));
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(n); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        h = hexa_add(h, hexa_call2(char_code, name, i));
        i = hexa_add(i, hexa_int(1));
    }
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(h); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        h = hexa_add(h, hexa_int(64));
    }
    return hexa_mod(h, hexa_int(64));
    return hexa_void();
}


HexaVal tc_scope_cache_init(void) {
    HexaVal b = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(64)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        b = hexa_array_push(b, hexa_array_new());
        i = hexa_add(i, hexa_int(1));
    }
    scope_cache = b;
    return hexa_void();
}


HexaVal tc_pop_scope(void) {
    HexaVal new_names = hexa_array_new();
    HexaVal new_types = hexa_array_new();
    HexaVal new_depths = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(scope_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_index_get(scope_depths, i)); HexaVal __r=(tc_depth); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            new_names = hexa_array_push(new_names, hexa_index_get(scope_names, i));
            new_types = hexa_array_push(new_types, hexa_index_get(scope_types, i));
            new_depths = hexa_array_push(new_depths, hexa_index_get(scope_depths, i));
        }
        i = hexa_add(i, hexa_int(1));
    }
    scope_names = new_names;
    scope_types = new_types;
    scope_depths = new_depths;
    tc_depth = hexa_sub(tc_depth, hexa_int(1));
    HexaVal cutoff = hexa_int(hexa_len(scope_names));
    if (hexa_truthy(hexa_eq(hexa_int(hexa_len(scope_cache)), hexa_int(64)))) {
        HexaVal bi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(bi); HexaVal __r=(hexa_int(64)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal bucket = hexa_index_get(scope_cache, bi);
            HexaVal nb = hexa_array_new();
            HexaVal k = hexa_int(0);
            HexaVal bn = hexa_int(hexa_len(bucket));
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(k); HexaVal __r=(bn); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                HexaVal e = hexa_index_get(bucket, k);
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_index_get(e, hexa_int(1))); HexaVal __r=(cutoff); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                    nb = hexa_array_push(nb, e);
                }
                k = hexa_add(k, hexa_int(1));
            }
            scope_cache = hexa_index_set(scope_cache, bi, nb);
            bi = hexa_add(bi, hexa_int(1));
        }
    }
    return hexa_void();
}


HexaVal tc_define(HexaVal name, HexaVal typ) {
    HexaVal idx = hexa_int(hexa_len(scope_names));
    scope_names = hexa_array_push(scope_names, name);
    scope_types = hexa_array_push(scope_types, typ);
    scope_depths = hexa_array_push(scope_depths, tc_depth);
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_int(hexa_len(scope_cache)), hexa_int(64)))))) {
        tc_scope_cache_init();
    }
    HexaVal b = tc_scope_hash(name);
    scope_cache = hexa_index_set(scope_cache, b, hexa_array_push(hexa_index_get(scope_cache, b), hexa_array_push(hexa_array_push(hexa_array_new(), name), idx)));
    return hexa_void();
}


HexaVal tc_lookup(HexaVal name) {
    if (hexa_truthy(hexa_eq(hexa_int(hexa_len(scope_cache)), hexa_int(64)))) {
        HexaVal bucket = hexa_index_get(scope_cache, tc_scope_hash(name));
        HexaVal best = hexa_sub(hexa_int(0), hexa_int(1));
        HexaVal bi = hexa_int(0);
        HexaVal bn = hexa_int(hexa_len(bucket));
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(bi); HexaVal __r=(bn); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal e = hexa_index_get(bucket, bi);
            if (hexa_truthy(hexa_eq(hexa_index_get(e, hexa_int(0)), name))) {
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_index_get(e, hexa_int(1))); HexaVal __r=(best); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                    best = hexa_index_get(e, hexa_int(1));
                }
            }
            bi = hexa_add(bi, hexa_int(1));
        }
        if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(best); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
            return hexa_index_get(scope_types, best);
        }
        return hexa_str("");
    }
    HexaVal i = hexa_sub(hexa_int(hexa_len(scope_names)), hexa_int(1));
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(scope_names, i), name))) {
            return hexa_index_get(scope_types, i);
        }
        i = hexa_sub(i, hexa_int(1));
    }
    return hexa_str("");
    return hexa_void();
}


HexaVal tc_fn_hash(HexaVal name) {
    HexaVal h = hexa_int(0);
    HexaVal i = hexa_int(0);
    HexaVal n = hexa_int(hexa_len(name));
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(n); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        h = hexa_add(h, hexa_call2(char_code, name, i));
        i = hexa_add(i, hexa_int(1));
    }
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(h); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        h = hexa_add(h, hexa_int(64));
    }
    return hexa_mod(h, hexa_int(64));
    return hexa_void();
}


HexaVal tc_fn_cache_init(void) {
    HexaVal b = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(64)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        b = hexa_array_push(b, hexa_array_new());
        i = hexa_add(i, hexa_int(1));
    }
    fn_cache = b;
    return hexa_void();
}


HexaVal tc_fn_cache_lookup(HexaVal name) {
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_int(hexa_len(fn_cache)), hexa_int(64)))))) {
        return hexa_sub(hexa_int(0), hexa_int(1));
    }
    HexaVal bucket = hexa_index_get(fn_cache, tc_fn_hash(name));
    HexaVal best = hexa_sub(hexa_int(0), hexa_int(1));
    HexaVal bi = hexa_int(0);
    HexaVal bn = hexa_int(hexa_len(bucket));
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(bi); HexaVal __r=(bn); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal e = hexa_index_get(bucket, bi);
        if (hexa_truthy(hexa_eq(hexa_index_get(e, hexa_int(0)), name))) {
            if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_index_get(e, hexa_int(1))); HexaVal __r=(best); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                best = hexa_index_get(e, hexa_int(1));
            }
        }
        bi = hexa_add(bi, hexa_int(1));
    }
    return best;
    return hexa_void();
}


HexaVal tc_register_fn(HexaVal name, HexaVal arity, HexaVal ret_type) {
    HexaVal idx = hexa_int(hexa_len(fn_names));
    fn_names = hexa_array_push(fn_names, name);
    fn_arities = hexa_array_push(fn_arities, arity);
    fn_ret_types = hexa_array_push(fn_ret_types, ret_type);
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_int(hexa_len(fn_cache)), hexa_int(64)))))) {
        tc_fn_cache_init();
    }
    HexaVal b = tc_fn_hash(name);
    fn_cache = hexa_index_set(fn_cache, b, hexa_array_push(hexa_index_get(fn_cache, b), hexa_array_push(hexa_array_push(hexa_array_new(), name), idx)));
    return hexa_void();
}


HexaVal tc_lookup_fn_arity(HexaVal name) {
    HexaVal idx = tc_fn_cache_lookup(name);
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(idx); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
        return hexa_index_get(fn_arities, idx);
    }
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(fn_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(fn_names, i), name))) {
            return hexa_index_get(fn_arities, i);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_sub(hexa_int(0), hexa_int(1));
    return hexa_void();
}


HexaVal tc_lookup_fn_ret(HexaVal name) {
    HexaVal idx = tc_fn_cache_lookup(name);
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(idx); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
        return hexa_index_get(fn_ret_types, idx);
    }
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(fn_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(fn_names, i), name))) {
            return hexa_index_get(fn_ret_types, i);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_str("unknown");
    return hexa_void();
}


HexaVal tc_register_struct(HexaVal name, HexaVal field_count) {
    struct_names = hexa_array_push(struct_names, name);
    struct_field_counts = hexa_array_push(struct_field_counts, field_count);
    struct_field_offsets = hexa_array_push(struct_field_offsets, hexa_int(hexa_len(struct_all_field_names)));
    return hexa_void();
}


HexaVal tc_register_struct_field(HexaVal fname, HexaVal ftype) {
    struct_all_field_names = hexa_array_push(struct_all_field_names, fname);
    struct_all_field_types = hexa_array_push(struct_all_field_types, ftype);
    return hexa_void();
}


HexaVal tc_register_enum(HexaVal name, HexaVal variant_count) {
    enum_names = hexa_array_push(enum_names, name);
    enum_variant_counts = hexa_array_push(enum_variant_counts, variant_count);
    enum_variant_offsets = hexa_array_push(enum_variant_offsets, hexa_int(hexa_len(enum_all_variant_names)));
    return hexa_void();
}


HexaVal tc_register_enum_variant(HexaVal vname) {
    enum_all_variant_names = hexa_array_push(enum_all_variant_names, vname);
    return hexa_void();
}


HexaVal tc_lookup_struct(HexaVal name) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(struct_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(struct_names, i), name))) {
            return hexa_index_get(struct_field_counts, i);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_sub(hexa_int(0), hexa_int(1));
    return hexa_void();
}


HexaVal tc_lookup_struct_field(HexaVal struct_name, HexaVal field_name) {
    HexaVal si = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(si); HexaVal __r=(hexa_int(hexa_len(struct_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(struct_names, si), struct_name))) {
            HexaVal offset = hexa_index_get(struct_field_offsets, si);
            HexaVal count = hexa_index_get(struct_field_counts, si);
            HexaVal fi = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                if (hexa_truthy(hexa_eq(hexa_index_get(struct_all_field_names, hexa_add(offset, fi)), field_name))) {
                    return hexa_index_get(struct_all_field_types, hexa_add(offset, fi));
                }
                fi = hexa_add(fi, hexa_int(1));
            }
            return hexa_str("");
        }
        si = hexa_add(si, hexa_int(1));
    }
    return hexa_str("");
    return hexa_void();
}


HexaVal tc_get_struct_field_names(HexaVal struct_name) {
    HexaVal result = hexa_array_new();
    HexaVal si = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(si); HexaVal __r=(hexa_int(hexa_len(struct_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(struct_names, si), struct_name))) {
            HexaVal offset = hexa_index_get(struct_field_offsets, si);
            HexaVal count = hexa_index_get(struct_field_counts, si);
            HexaVal fi = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                result = hexa_array_push(result, hexa_index_get(struct_all_field_names, hexa_add(offset, fi)));
                fi = hexa_add(fi, hexa_int(1));
            }
            return result;
        }
        si = hexa_add(si, hexa_int(1));
    }
    return result;
    return hexa_void();
}


HexaVal tc_lookup_enum(HexaVal name) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(enum_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(enum_names, i), name))) {
            return hexa_index_get(enum_variant_counts, i);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_sub(hexa_int(0), hexa_int(1));
    return hexa_void();
}


HexaVal tc_get_enum_variants(HexaVal name) {
    HexaVal result = hexa_array_new();
    HexaVal ei = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ei); HexaVal __r=(hexa_int(hexa_len(enum_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(enum_names, ei), name))) {
            HexaVal offset = hexa_index_get(enum_variant_offsets, ei);
            HexaVal count = hexa_index_get(enum_variant_counts, ei);
            HexaVal vi = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(vi); HexaVal __r=(count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                result = hexa_array_push(result, hexa_index_get(enum_all_variant_names, hexa_add(offset, vi)));
                vi = hexa_add(vi, hexa_int(1));
            }
            return result;
        }
        ei = hexa_add(ei, hexa_int(1));
    }
    return result;
    return hexa_void();
}


HexaVal tc_warn(HexaVal msg) {
    tc_errors = hexa_array_push(tc_errors, TypeError(hexa_add(hexa_str("[warn] "), msg), hexa_str("")));
    return hexa_void();
}


HexaVal tc_warn_at(HexaVal name, HexaVal msg) {
    tc_errors = hexa_array_push(tc_errors, TypeError(hexa_add(hexa_str("[warn] "), msg), name));
    return hexa_void();
}


HexaVal tc_register_generic_struct(HexaVal name, HexaVal tparams) {
    HexaVal count = hexa_int(hexa_len(tparams));
    if (hexa_truthy(hexa_eq(count, hexa_int(0)))) {
        return hexa_void();
    }
    generic_struct_names = hexa_array_push(generic_struct_names, name);
    generic_struct_param_counts = hexa_array_push(generic_struct_param_counts, count);
    generic_struct_param_offsets = hexa_array_push(generic_struct_param_offsets, hexa_int(hexa_len(generic_all_param_names)));
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        generic_all_param_names = hexa_array_push(generic_all_param_names, hexa_map_get_ic(hexa_index_get(tparams, i), "name", &__hexa_type_checker_ic_0));
        HexaVal bound = hexa_map_get_ic(hexa_index_get(tparams, i), "value", &__hexa_type_checker_ic_1);
        if (hexa_truthy(hexa_eq(bound, hexa_str("")))) {
            generic_all_param_bounds = hexa_array_push(generic_all_param_bounds, hexa_str(""));
        } else {
            generic_all_param_bounds = hexa_array_push(generic_all_param_bounds, bound);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_void();
}


HexaVal tc_register_generic_fn(HexaVal name, HexaVal tparams) {
    HexaVal count = hexa_int(hexa_len(tparams));
    if (hexa_truthy(hexa_eq(count, hexa_int(0)))) {
        return hexa_void();
    }
    generic_fn_names = hexa_array_push(generic_fn_names, name);
    generic_fn_param_counts = hexa_array_push(generic_fn_param_counts, count);
    generic_fn_param_offsets = hexa_array_push(generic_fn_param_offsets, hexa_int(hexa_len(generic_fn_all_param_names)));
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        generic_fn_all_param_names = hexa_array_push(generic_fn_all_param_names, hexa_map_get_ic(hexa_index_get(tparams, i), "name", &__hexa_type_checker_ic_2));
        HexaVal bound = hexa_map_get_ic(hexa_index_get(tparams, i), "value", &__hexa_type_checker_ic_3);
        if (hexa_truthy(hexa_eq(bound, hexa_str("")))) {
            generic_fn_all_param_bounds = hexa_array_push(generic_fn_all_param_bounds, hexa_str(""));
        } else {
            generic_fn_all_param_bounds = hexa_array_push(generic_fn_all_param_bounds, bound);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_void();
}


HexaVal tc_lookup_generic_struct_param_count(HexaVal name) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(generic_struct_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(generic_struct_names, i), name))) {
            return hexa_index_get(generic_struct_param_counts, i);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_int(0);
    return hexa_void();
}


HexaVal tc_get_generic_struct_params(HexaVal name) {
    HexaVal result = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(generic_struct_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(generic_struct_names, i), name))) {
            HexaVal offset = hexa_index_get(generic_struct_param_offsets, i);
            HexaVal count = hexa_index_get(generic_struct_param_counts, i);
            HexaVal j = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(j); HexaVal __r=(count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                result = hexa_array_push(result, hexa_index_get(generic_all_param_names, hexa_add(offset, j)));
                j = hexa_add(j, hexa_int(1));
            }
            return result;
        }
        i = hexa_add(i, hexa_int(1));
    }
    return result;
    return hexa_void();
}


HexaVal tc_get_generic_struct_bounds(HexaVal name) {
    HexaVal result = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(generic_struct_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(generic_struct_names, i), name))) {
            HexaVal offset = hexa_index_get(generic_struct_param_offsets, i);
            HexaVal count = hexa_index_get(generic_struct_param_counts, i);
            HexaVal j = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(j); HexaVal __r=(count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                result = hexa_array_push(result, hexa_index_get(generic_all_param_bounds, hexa_add(offset, j)));
                j = hexa_add(j, hexa_int(1));
            }
            return result;
        }
        i = hexa_add(i, hexa_int(1));
    }
    return result;
    return hexa_void();
}


HexaVal tc_lookup_generic_fn_param_count(HexaVal name) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(generic_fn_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(generic_fn_names, i), name))) {
            return hexa_index_get(generic_fn_param_counts, i);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_int(0);
    return hexa_void();
}


HexaVal tc_get_generic_fn_params(HexaVal name) {
    HexaVal result = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(generic_fn_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(generic_fn_names, i), name))) {
            HexaVal offset = hexa_index_get(generic_fn_param_offsets, i);
            HexaVal count = hexa_index_get(generic_fn_param_counts, i);
            HexaVal j = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(j); HexaVal __r=(count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                result = hexa_array_push(result, hexa_index_get(generic_fn_all_param_names, hexa_add(offset, j)));
                j = hexa_add(j, hexa_int(1));
            }
            return result;
        }
        i = hexa_add(i, hexa_int(1));
    }
    return result;
    return hexa_void();
}


HexaVal tc_get_generic_fn_bounds(HexaVal name) {
    HexaVal result = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(generic_fn_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(generic_fn_names, i), name))) {
            HexaVal offset = hexa_index_get(generic_fn_param_offsets, i);
            HexaVal count = hexa_index_get(generic_fn_param_counts, i);
            HexaVal j = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(j); HexaVal __r=(count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                result = hexa_array_push(result, hexa_index_get(generic_fn_all_param_bounds, hexa_add(offset, j)));
                j = hexa_add(j, hexa_int(1));
            }
            return result;
        }
        i = hexa_add(i, hexa_int(1));
    }
    return result;
    return hexa_void();
}


HexaVal tc_push_type_params(HexaVal tparams) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(tparams))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal tp = hexa_index_get(tparams, i);
        tparam_names = hexa_array_push(tparam_names, hexa_map_get_ic(tp, "name", &__hexa_type_checker_ic_4));
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(tp, "value", &__hexa_type_checker_ic_5), hexa_str("")))))) {
            tparam_bound = hexa_array_push(tparam_bound, hexa_map_get_ic(tp, "value", &__hexa_type_checker_ic_6));
        } else {
            tparam_bound = hexa_array_push(tparam_bound, hexa_str(""));
        }
        tc_define(hexa_map_get_ic(tp, "name", &__hexa_type_checker_ic_7), hexa_str("typeparam"));
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_void();
}


HexaVal tc_pop_type_params(HexaVal tparams) {
    HexaVal count = hexa_int(hexa_len(tparams));
    if (hexa_truthy(hexa_eq(count, hexa_int(0)))) {
        return hexa_void();
    }
    HexaVal nn = hexa_array_new();
    HexaVal nb = hexa_array_new();
    HexaVal i = hexa_int(0);
    HexaVal target = hexa_sub(hexa_int(hexa_len(tparam_names)), count);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(target); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        nn = hexa_array_push(nn, hexa_index_get(tparam_names, i));
        nb = hexa_array_push(nb, hexa_index_get(tparam_bound, i));
        i = hexa_add(i, hexa_int(1));
    }
    tparam_names = nn;
    tparam_bound = nb;
    return hexa_void();
}


HexaVal tc_is_type_param(HexaVal name) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(tparam_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(tparam_names, i), name))) {
            return hexa_bool(1);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal tc_get_type_param_bound(HexaVal name) {
    HexaVal i = hexa_sub(hexa_int(hexa_len(tparam_names)), hexa_int(1));
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(tparam_names, i), name))) {
            return hexa_index_get(tparam_bound, i);
        }
        i = hexa_sub(i, hexa_int(1));
    }
    return hexa_str("");
    return hexa_void();
}


HexaVal tc_validate_type_args(HexaVal struct_name, HexaVal type_args) {
    HexaVal expected = tc_lookup_generic_struct_param_count(struct_name);
    HexaVal actual = hexa_int(hexa_len(type_args));
    if (hexa_truthy(hexa_eq(expected, hexa_int(0)))) {
        if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(actual); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
            tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Struct '"), struct_name), hexa_str("' is not generic but given ")), hexa_to_string(actual)), hexa_str(" type arguments")));
        }
        return hexa_void();
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(actual, expected))))) {
        tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Struct '"), struct_name), hexa_str("' expects ")), hexa_to_string(expected)), hexa_str(" type params, got ")), hexa_to_string(actual)));
        return hexa_void();
    }
    HexaVal bounds = tc_get_generic_struct_bounds(struct_name);
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(actual); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal bound = hexa_index_get(bounds, i);
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(bound, hexa_str("")))))) {
            HexaVal arg_name = hexa_map_get_ic(hexa_index_get(type_args, i), "name", &__hexa_type_checker_ic_8);
            HexaVal arg_type = tc_lookup(arg_name);
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(arg_type, hexa_str(""))) && hexa_truthy(hexa_bool(!hexa_truthy(tc_is_type_param(arg_name))))))) {
                HexaVal at = annotation_to_type(arg_name);
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(at, arg_name)) && hexa_truthy(hexa_eq(tc_lookup_struct(arg_name), hexa_sub(hexa_int(0), hexa_int(1)))))) && hexa_truthy(hexa_eq(tc_lookup_enum(arg_name), hexa_sub(hexa_int(0), hexa_int(1))))))) {
                    tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Unknown type '"), arg_name), hexa_str("' used as type argument for '")), struct_name), hexa_str("'")));
                }
            }
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_void();
}


HexaVal tc_validate_fn_type_args(HexaVal fn_name, HexaVal type_args) {
    HexaVal expected = tc_lookup_generic_fn_param_count(fn_name);
    HexaVal actual = hexa_int(hexa_len(type_args));
    if (hexa_truthy(hexa_eq(expected, hexa_int(0)))) {
        if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(actual); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
            tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Function '"), fn_name), hexa_str("' is not generic but given ")), hexa_to_string(actual)), hexa_str(" type arguments")));
        }
        return hexa_void();
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(actual, expected))))) {
        tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Function '"), fn_name), hexa_str("' expects ")), hexa_to_string(expected)), hexa_str(" type params, got ")), hexa_to_string(actual)));
        return hexa_void();
    }
    return hexa_void();
}


HexaVal tc_register_builtins(void) {
    tc_register_fn(hexa_str("println"), hexa_sub(hexa_int(0), hexa_int(1)), hexa_str("void"));
    tc_register_fn(hexa_str("print"), hexa_sub(hexa_int(0), hexa_int(1)), hexa_str("void"));
    tc_register_fn(hexa_str("format"), hexa_sub(hexa_int(0), hexa_int(1)), hexa_str("string"));
    tc_register_fn(hexa_str("len"), hexa_int(1), hexa_str("int"));
    tc_register_fn(hexa_str("to_string"), hexa_int(1), hexa_str("string"));
    tc_register_fn(hexa_str("is_alpha"), hexa_int(1), hexa_str("bool"));
    tc_register_fn(hexa_str("is_digit"), hexa_int(1), hexa_str("bool"));
    tc_register_fn(hexa_str("is_alphanumeric"), hexa_int(1), hexa_str("bool"));
    tc_register_fn(hexa_str("read_file"), hexa_int(1), hexa_str("string"));
    tc_register_fn(hexa_str("type_of"), hexa_int(1), hexa_str("string"));
    tc_register_fn(hexa_str("int"), hexa_int(1), hexa_str("int"));
    tc_register_fn(hexa_str("float"), hexa_int(1), hexa_str("float"));
    tc_register_fn(hexa_str("string"), hexa_int(1), hexa_str("string"));
    tc_register_fn(hexa_str("push"), hexa_int(2), hexa_str("array"));
    tc_register_fn(hexa_str("sigma"), hexa_int(1), hexa_str("int"));
    tc_register_fn(hexa_str("phi"), hexa_int(1), hexa_str("int"));
    tc_register_fn(hexa_str("tau"), hexa_int(1), hexa_str("int"));
    return hexa_void();
}


HexaVal annotation_to_type(HexaVal ann) {
    if (hexa_truthy(hexa_eq(ann, hexa_str("")))) {
        return hexa_str("unknown");
    }
    if (hexa_truthy(hexa_eq(ann, hexa_str("int")))) {
        return hexa_str("int");
    }
    if (hexa_truthy(hexa_eq(ann, hexa_str("float")))) {
        return hexa_str("float");
    }
    if (hexa_truthy(hexa_eq(ann, hexa_str("bool")))) {
        return hexa_str("bool");
    }
    if (hexa_truthy(hexa_eq(ann, hexa_str("string")))) {
        return hexa_str("string");
    }
    if (hexa_truthy(hexa_eq(ann, hexa_str("char")))) {
        return hexa_str("char");
    }
    if (hexa_truthy(hexa_eq(ann, hexa_str("void")))) {
        return hexa_str("void");
    }
    if (hexa_truthy(hexa_eq(ann, hexa_str("any")))) {
        return hexa_str("any");
    }
    if (hexa_truthy(hexa_eq(ann, hexa_str("array")))) {
        return hexa_str("array");
    }
    if (hexa_truthy(tc_is_type_param(ann))) {
        return ann;
    }
    return ann;
    return hexa_void();
}


HexaVal types_compatible(HexaVal expected, HexaVal actual) {
    if (hexa_truthy(hexa_eq(expected, hexa_str("unknown")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(actual, hexa_str("unknown")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(expected, hexa_str("any")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(actual, hexa_str("any")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(expected, actual))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(expected, hexa_str("float"))) && hexa_truthy(hexa_eq(actual, hexa_str("int")))))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(expected, hexa_str("typeparam")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(actual, hexa_str("typeparam")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(tc_is_type_param(expected))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(tc_is_type_param(actual))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal tc_infer_expr(HexaVal node) {
    HexaVal i = hexa_void();
    if (hexa_truthy(hexa_eq(node, hexa_str("")))) {
        return hexa_str("void");
    }
    HexaVal k = hexa_map_get_ic(node, "kind", &__hexa_type_checker_ic_9);
    if (hexa_truthy(hexa_eq(k, hexa_str("IntLit")))) {
        return hexa_str("int");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("FloatLit")))) {
        return hexa_str("float");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BoolLit")))) {
        return hexa_str("bool");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StringLit")))) {
        return hexa_str("string");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("CharLit")))) {
        return hexa_str("char");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Array")))) {
        return hexa_str("array");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Tuple")))) {
        return hexa_str("tuple");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Wildcard")))) {
        return hexa_str("any");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Range")))) {
        tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_10));
        tc_infer_expr(hexa_map_get_ic(node, "right", &__hexa_type_checker_ic_11));
        return hexa_str("range");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Lambda")))) {
        return hexa_str("fn");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Ident")))) {
        HexaVal typ = tc_lookup(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_12));
        if (hexa_truthy(hexa_eq(typ, hexa_str("")))) {
            tc_error(hexa_add(hexa_add(hexa_str("Undeclared variable '"), hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_13)), hexa_str("'")));
            return hexa_str("unknown");
        }
        return typ;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BinOp")))) {
        HexaVal lt = tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_14));
        HexaVal rt = tc_infer_expr(hexa_map_get_ic(node, "right", &__hexa_type_checker_ic_15));
        HexaVal op = hexa_map_get_ic(node, "op", &__hexa_type_checker_ic_16);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(op, hexa_str("=="))) || hexa_truthy(hexa_eq(op, hexa_str("!="))))) || hexa_truthy(hexa_eq(op, hexa_str("<"))))) || hexa_truthy(hexa_eq(op, hexa_str(">"))))) || hexa_truthy(hexa_eq(op, hexa_str("<="))))) || hexa_truthy(hexa_eq(op, hexa_str(">=")))))) {
            return hexa_str("bool");
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("??")))) {
            return rt;
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(op, hexa_str("&&"))) || hexa_truthy(hexa_eq(op, hexa_str("||"))))) || hexa_truthy(hexa_eq(op, hexa_str("^^")))))) {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(lt, hexa_str("bool"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(lt, hexa_str("unknown")))))))) {
                tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Logical operator '"), op), hexa_str("' expects bool, got '")), lt), hexa_str("'")));
            }
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(rt, hexa_str("bool"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(rt, hexa_str("unknown")))))))) {
                tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Logical operator '"), op), hexa_str("' expects bool, got '")), rt), hexa_str("'")));
            }
            return hexa_str("bool");
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("+")))) {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(lt, hexa_str("string"))) || hexa_truthy(hexa_eq(rt, hexa_str("string")))))) {
                return hexa_str("string");
            }
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(op, hexa_str("+"))) || hexa_truthy(hexa_eq(op, hexa_str("-"))))) || hexa_truthy(hexa_eq(op, hexa_str("*"))))) || hexa_truthy(hexa_eq(op, hexa_str("/"))))) || hexa_truthy(hexa_eq(op, hexa_str("%"))))) || hexa_truthy(hexa_eq(op, hexa_str("**")))))) {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(lt, hexa_str("float"))) || hexa_truthy(hexa_eq(rt, hexa_str("float")))))) {
                return hexa_str("float");
            }
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(lt, hexa_str("int"))) && hexa_truthy(hexa_eq(rt, hexa_str("int")))))) {
                return hexa_str("int");
            }
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(types_compatible(lt, rt)))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(lt, hexa_str("unknown"))))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(rt, hexa_str("unknown")))))))) {
                tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Arithmetic type mismatch: '"), lt), hexa_str("' ")), op), hexa_str(" '")), rt), hexa_str("'")));
            }
            return lt;
        }
        return hexa_str("unknown");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("UnaryOp")))) {
        HexaVal ot = tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_17));
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(node, "op", &__hexa_type_checker_ic_18), hexa_str("!")))) {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(ot, hexa_str("bool"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(ot, hexa_str("unknown")))))))) {
                tc_error(hexa_add(hexa_add(hexa_str("'!' operator expects bool, got '"), ot), hexa_str("'")));
            }
            return hexa_str("bool");
        }
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(node, "op", &__hexa_type_checker_ic_19), hexa_str("-")))) {
            return ot;
        }
        return ot;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Call")))) {
        HexaVal callee = hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_20);
        HexaVal arg_count = hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_type_checker_ic_21)));
        i = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(arg_count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            tc_infer_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_type_checker_ic_22), i));
            i = hexa_add(i, hexa_int(1));
        }
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(callee, "kind", &__hexa_type_checker_ic_23), hexa_str("Ident")))) {
            HexaVal fn_arity = tc_lookup_fn_arity(hexa_map_get_ic(callee, "name", &__hexa_type_checker_ic_24));
            if (hexa_truthy(hexa_eq(fn_arity, hexa_sub(hexa_int(0), hexa_int(1))))) {
                return hexa_str("unknown");
            }
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fn_arity); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); }))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(fn_arity, arg_count))))))) {
                tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Function '"), hexa_map_get_ic(callee, "name", &__hexa_type_checker_ic_25)), hexa_str("' expects ")), hexa_to_string(fn_arity)), hexa_str(" args, got ")), hexa_to_string(arg_count)));
            }
            return tc_lookup_fn_ret(hexa_map_get_ic(callee, "name", &__hexa_type_checker_ic_26));
        }
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(callee, "kind", &__hexa_type_checker_ic_27), hexa_str("Field")))) {
            tc_infer_expr(hexa_map_get_ic(callee, "left", &__hexa_type_checker_ic_28));
            return hexa_str("unknown");
        }
        return hexa_str("unknown");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Field")))) {
        HexaVal obj_type = tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_29));
        HexaVal field_name = hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_30);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(obj_type, hexa_str("unknown"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(obj_type, hexa_str("any"))))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(tc_lookup_struct(obj_type), hexa_sub(hexa_int(0), hexa_int(1))))))))) {
            HexaVal ftype = tc_lookup_struct_field(obj_type, field_name);
            if (hexa_truthy(hexa_eq(ftype, hexa_str("")))) {
                HexaVal known = tc_get_struct_field_names(obj_type);
                HexaVal hint = hexa_str("");
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(known))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                    hint = hexa_str(" (known fields: ");
                    HexaVal fi = hexa_int(0);
                    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(hexa_int(hexa_len(known))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                        if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                            hint = hexa_add(hint, hexa_str(", "));
                        }
                        hint = hexa_add(hint, hexa_index_get(known, fi));
                        fi = hexa_add(fi, hexa_int(1));
                    }
                    hint = hexa_add(hint, hexa_str(")"));
                }
                tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Struct '"), obj_type), hexa_str("' has no field '")), field_name), hexa_str("'")), hint));
                return hexa_str("unknown");
            }
            return annotation_to_type(ftype);
        }
        return hexa_str("unknown");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Index")))) {
        tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_31));
        HexaVal idx_type = tc_infer_expr(hexa_map_get_ic(node, "right", &__hexa_type_checker_ic_32));
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(idx_type, hexa_str("int"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(idx_type, hexa_str("unknown")))))))) {
            tc_error(hexa_add(hexa_add(hexa_str("Array index must be int, got '"), idx_type), hexa_str("'")));
        }
        return hexa_str("unknown");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("IfExpr")))) {
        HexaVal cond_type = tc_infer_expr(hexa_map_get_ic(node, "cond", &__hexa_type_checker_ic_33));
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(cond_type, hexa_str("bool"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(cond_type, hexa_str("unknown")))))))) {
            tc_error(hexa_add(hexa_add(hexa_str("If condition must be bool, got '"), cond_type), hexa_str("'")));
        }
        tc_push_scope();
        tc_check_stmts(hexa_map_get_ic(node, "then_body", &__hexa_type_checker_ic_34));
        tc_pop_scope();
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "else_body", &__hexa_type_checker_ic_35), hexa_str(""))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(hexa_map_get_ic(node, "else_body", &__hexa_type_checker_ic_36)))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))))) {
            tc_push_scope();
            tc_check_stmts(hexa_map_get_ic(node, "else_body", &__hexa_type_checker_ic_37));
            tc_pop_scope();
        }
        return hexa_str("unknown");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("MatchExpr")))) {
        HexaVal match_type = tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_38));
        HexaVal arm_count = hexa_int(hexa_len(hexa_map_get_ic(node, "arms", &__hexa_type_checker_ic_39)));
        HexaVal has_wildcard = hexa_bool(0);
        HexaVal covered_variants = hexa_array_new();
        i = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(arm_count); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal arm = hexa_index_get(hexa_map_get_ic(node, "arms", &__hexa_type_checker_ic_40), i);
            HexaVal pat = hexa_map_get_ic(arm, "left", &__hexa_type_checker_ic_41);
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(pat, hexa_str(""))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(pat, "kind", &__hexa_type_checker_ic_42), hexa_str("Wildcard")))))) {
                has_wildcard = hexa_bool(1);
            }
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(pat, hexa_str(""))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(pat, "kind", &__hexa_type_checker_ic_43), hexa_str("EnumPath")))))) {
                covered_variants = hexa_array_push(covered_variants, hexa_map_get_ic(pat, "name", &__hexa_type_checker_ic_44));
            }
            tc_push_scope();
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(pat, hexa_str(""))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(pat, "kind", &__hexa_type_checker_ic_45), hexa_str("Ident")))))) {
                tc_define(hexa_map_get_ic(pat, "name", &__hexa_type_checker_ic_46), match_type);
            }
            tc_check_stmts(hexa_map_get_ic(arm, "body", &__hexa_type_checker_ic_47));
            tc_pop_scope();
            i = hexa_add(i, hexa_int(1));
        }
        if (hexa_truthy(hexa_bool(!hexa_truthy(has_wildcard)))) {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(match_type, hexa_str("unknown"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(match_type, hexa_str("any"))))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(tc_lookup_enum(match_type), hexa_sub(hexa_int(0), hexa_int(1))))))))) {
                HexaVal all_variants = tc_get_enum_variants(match_type);
                HexaVal missing = hexa_array_new();
                HexaVal vi = hexa_int(0);
                while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(vi); HexaVal __r=(hexa_int(hexa_len(all_variants))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                    HexaVal found = hexa_bool(0);
                    HexaVal ci = hexa_int(0);
                    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ci); HexaVal __r=(hexa_int(hexa_len(covered_variants))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                        if (hexa_truthy(hexa_eq(hexa_index_get(covered_variants, ci), hexa_index_get(all_variants, vi)))) {
                            found = hexa_bool(1);
                        }
                        ci = hexa_add(ci, hexa_int(1));
                    }
                    if (hexa_truthy(hexa_bool(!hexa_truthy(found)))) {
                        missing = hexa_array_push(missing, hexa_index_get(all_variants, vi));
                    }
                    vi = hexa_add(vi, hexa_int(1));
                }
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(missing))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                    HexaVal miss_str = hexa_str("");
                    HexaVal mi = hexa_int(0);
                    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(mi); HexaVal __r=(hexa_int(hexa_len(missing))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                        if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(mi); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                            miss_str = hexa_add(miss_str, hexa_str(", "));
                        }
                        miss_str = hexa_add(miss_str, hexa_index_get(missing, mi));
                        mi = hexa_add(mi, hexa_int(1));
                    }
                    tc_warn(hexa_add(hexa_str("Match may not be exhaustive — missing variants: "), miss_str));
                }
            } else {
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(arm_count); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                    tc_warn(hexa_str("Match has no wildcard '_' arm — may not be exhaustive"));
                }
            }
        }
        return hexa_str("unknown");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StructInit")))) {
        HexaVal sc = tc_lookup_struct(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_48));
        if (hexa_truthy(hexa_eq(sc, hexa_sub(hexa_int(0), hexa_int(1))))) {
            tc_error(hexa_add(hexa_add(hexa_str("Unknown struct '"), hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_49)), hexa_str("'")));
        } else {
            HexaVal si_type_args = hexa_map_get_ic(node, "items", &__hexa_type_checker_ic_50);
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(si_type_args, hexa_str(""))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(si_type_args))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))))) {
                tc_validate_type_args(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_51), si_type_args);
            } else {
                HexaVal expected_tp = tc_lookup_generic_struct_param_count(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_52));
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(expected_tp); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                    tc_warn(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Generic struct '"), hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_53)), hexa_str("' used without type arguments (expected ")), hexa_to_string(expected_tp)), hexa_str(")")));
                }
            }
            i = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_type_checker_ic_54)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                HexaVal fld = hexa_index_get(hexa_map_get_ic(node, "fields", &__hexa_type_checker_ic_55), i);
                HexaVal init_type = tc_infer_expr(hexa_map_get_ic(fld, "left", &__hexa_type_checker_ic_56));
                HexaVal expected_type = tc_lookup_struct_field(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_57), hexa_map_get_ic(fld, "name", &__hexa_type_checker_ic_58));
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(expected_type, hexa_str(""))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(fld, "name", &__hexa_type_checker_ic_59), hexa_str("")))))))) {
                    tc_error(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Struct '"), hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_60)), hexa_str("' has no field '")), hexa_map_get_ic(fld, "name", &__hexa_type_checker_ic_61)), hexa_str("'")));
                } else {
                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(expected_type, hexa_str(""))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(init_type, hexa_str("unknown")))))))) {
                        HexaVal et = annotation_to_type(expected_type);
                        if (hexa_truthy(hexa_bool(!hexa_truthy(types_compatible(et, init_type))))) {
                            tc_error_at(hexa_map_get_ic(fld, "name", &__hexa_type_checker_ic_62), hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Field type mismatch: expected '"), et), hexa_str("', got '")), init_type), hexa_str("'")));
                        }
                    }
                }
                i = hexa_add(i, hexa_int(1));
            }
            if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_type_checker_ic_63))), sc))))) {
                tc_warn(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Struct '"), hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_64)), hexa_str("' has ")), hexa_to_string(sc)), hexa_str(" fields, but ")), hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_type_checker_ic_65))))), hexa_str(" provided")));
            }
        }
        return hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_66);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("EnumPath")))) {
        return hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_67);
    }
    return hexa_str("unknown");
    return hexa_void();
}


HexaVal tc_check_stmt(HexaVal node) {
    HexaVal typ = hexa_void();
    HexaVal ann = hexa_void();
    HexaVal i = hexa_void();
    HexaVal k = hexa_map_get_ic(node, "kind", &__hexa_type_checker_ic_68);
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("LetStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("LetMutStmt")))))) {
        typ = tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_69));
        ann = annotation_to_type(hexa_map_get_ic(node, "value", &__hexa_type_checker_ic_70));
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(ann, hexa_str("unknown"))))) && hexa_truthy(hexa_bool(!hexa_truthy(types_compatible(ann, typ))))))) {
            tc_error_at(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_71), hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Type mismatch: declared '"), ann), hexa_str("' but assigned '")), typ), hexa_str("'")));
        }
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(ann, hexa_str("unknown")))))) {
            tc_define(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_72), ann);
        } else {
            tc_define(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_73), typ);
        }
        return hexa_void();
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("ConstStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("StaticStmt")))))) {
        typ = tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_74));
        ann = annotation_to_type(hexa_map_get_ic(node, "value", &__hexa_type_checker_ic_75));
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(ann, hexa_str("unknown")))))) {
            tc_define(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_76), ann);
        } else {
            tc_define(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_77), typ);
        }
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("FnDecl")))) {
        HexaVal arity = hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_type_checker_ic_78)));
        HexaVal fn_tparams = hexa_map_get_ic(node, "items", &__hexa_type_checker_ic_79);
        HexaVal has_tparams = hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(fn_tparams, hexa_str(""))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(fn_tparams))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); }))));
        if (hexa_truthy(has_tparams)) {
            tc_register_generic_fn(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_80), fn_tparams);
        }
        HexaVal ret = annotation_to_type(hexa_map_get_ic(node, "ret_type", &__hexa_type_checker_ic_81));
        tc_register_fn(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_82), arity, ret);
        tc_define(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_83), hexa_str("fn"));
        HexaVal prev_fn_ret = current_fn_ret_type;
        HexaVal prev_fn_name = current_fn_name;
        current_fn_ret_type = ret;
        current_fn_name = hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_84);
        tc_push_scope();
        if (hexa_truthy(has_tparams)) {
            tc_push_type_params(fn_tparams);
        }
        i = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(arity); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal p = hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_type_checker_ic_85), i);
            HexaVal ptype = annotation_to_type(hexa_map_get_ic(p, "value", &__hexa_type_checker_ic_86));
            tc_define(hexa_map_get_ic(p, "name", &__hexa_type_checker_ic_87), ptype);
            i = hexa_add(i, hexa_int(1));
        }
        tc_check_stmts(hexa_map_get_ic(node, "body", &__hexa_type_checker_ic_88));
        tc_pop_scope();
        if (hexa_truthy(has_tparams)) {
            tc_pop_type_params(fn_tparams);
        }
        current_fn_ret_type = prev_fn_ret;
        current_fn_name = prev_fn_name;
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StructDecl")))) {
        HexaVal fc = hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_type_checker_ic_89)));
        tc_register_struct(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_90), fc);
        HexaVal st_tparams = hexa_map_get_ic(node, "items", &__hexa_type_checker_ic_91);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(st_tparams, hexa_str(""))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(st_tparams))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))))) {
            tc_register_generic_struct(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_92), st_tparams);
        }
        HexaVal fi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(fc); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal f = hexa_index_get(hexa_map_get_ic(node, "fields", &__hexa_type_checker_ic_93), fi);
            tc_register_struct_field(hexa_map_get_ic(f, "name", &__hexa_type_checker_ic_94), hexa_map_get_ic(f, "value", &__hexa_type_checker_ic_95));
            fi = hexa_add(fi, hexa_int(1));
        }
        tc_define(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_96), hexa_str("type"));
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("EnumDecl")))) {
        HexaVal vc = hexa_int(hexa_len(hexa_map_get_ic(node, "variants", &__hexa_type_checker_ic_97)));
        tc_register_enum(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_98), vc);
        HexaVal vi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(vi); HexaVal __r=(vc); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            tc_register_enum_variant(hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "variants", &__hexa_type_checker_ic_99), vi), "name", &__hexa_type_checker_ic_100));
            vi = hexa_add(vi, hexa_int(1));
        }
        tc_define(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_101), hexa_str("type"));
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("TraitDecl")))) {
        tc_define(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_102), hexa_str("type"));
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ImplBlock")))) {
        tc_push_scope();
        i = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "methods", &__hexa_type_checker_ic_103)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            tc_check_stmt(hexa_index_get(hexa_map_get_ic(node, "methods", &__hexa_type_checker_ic_104), i));
            i = hexa_add(i, hexa_int(1));
        }
        tc_pop_scope();
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ForStmt")))) {
        tc_infer_expr(hexa_map_get_ic(node, "iter_expr", &__hexa_type_checker_ic_105));
        tc_push_scope();
        tc_define(hexa_map_get_ic(node, "name", &__hexa_type_checker_ic_106), hexa_str("unknown"));
        tc_check_stmts(hexa_map_get_ic(node, "body", &__hexa_type_checker_ic_107));
        tc_pop_scope();
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("WhileStmt")))) {
        HexaVal cond_type = tc_infer_expr(hexa_map_get_ic(node, "cond", &__hexa_type_checker_ic_108));
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(cond_type, hexa_str("bool"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(cond_type, hexa_str("unknown")))))))) {
            tc_error(hexa_add(hexa_add(hexa_str("While condition must be bool, got '"), cond_type), hexa_str("'")));
        }
        tc_push_scope();
        tc_check_stmts(hexa_map_get_ic(node, "body", &__hexa_type_checker_ic_109));
        tc_pop_scope();
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("LoopStmt")))) {
        tc_push_scope();
        tc_check_stmts(hexa_map_get_ic(node, "body", &__hexa_type_checker_ic_110));
        tc_pop_scope();
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ReturnStmt")))) {
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_111), hexa_str("")))))) {
            HexaVal ret_val_type = tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_112));
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(current_fn_ret_type, hexa_str("unknown"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(current_fn_ret_type, hexa_str("void")))))))) {
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(types_compatible(current_fn_ret_type, ret_val_type)))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(ret_val_type, hexa_str("unknown")))))))) {
                    tc_error_at(current_fn_name, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("Return type mismatch: expected '"), current_fn_ret_type), hexa_str("', got '")), ret_val_type), hexa_str("'")));
                }
            }
        } else {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(current_fn_ret_type, hexa_str("unknown"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(current_fn_ret_type, hexa_str("void")))))))) {
                tc_warn_at(current_fn_name, hexa_add(hexa_add(hexa_str("Bare 'return' in function expecting '"), current_fn_ret_type), hexa_str("'")));
            }
        }
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("AssignStmt")))) {
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_113), hexa_str(""))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_114), "kind", &__hexa_type_checker_ic_115), hexa_str("Ident")))))) {
            typ = tc_lookup(hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_116), "name", &__hexa_type_checker_ic_117));
            if (hexa_truthy(hexa_eq(typ, hexa_str("")))) {
                tc_error(hexa_add(hexa_add(hexa_str("Assignment to undeclared variable '"), hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_118), "name", &__hexa_type_checker_ic_119)), hexa_str("'")));
            }
        }
        tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_120));
        tc_infer_expr(hexa_map_get_ic(node, "right", &__hexa_type_checker_ic_121));
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ExprStmt")))) {
        tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_122));
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("AssertStmt")))) {
        HexaVal t = tc_infer_expr(hexa_map_get_ic(node, "left", &__hexa_type_checker_ic_123));
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(t, hexa_str("bool"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(t, hexa_str("unknown")))))))) {
            tc_error(hexa_add(hexa_add(hexa_str("Assert expects bool expression, got '"), t), hexa_str("'")));
        }
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("UseStmt")))) {
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ModStmt")))) {
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ImportStmt")))) {
        return hexa_void();
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ProofStmt")))) {
        tc_push_scope();
        tc_check_stmts(hexa_map_get_ic(node, "body", &__hexa_type_checker_ic_124));
        tc_pop_scope();
        return hexa_void();
    }
    return hexa_void();
}


HexaVal tc_check_stmts(HexaVal stmts) {
    if (hexa_truthy(hexa_eq(stmts, hexa_str("")))) {
        return hexa_void();
    }
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(stmts))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        tc_check_stmt(hexa_index_get(stmts, i));
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_void();
}


HexaVal tc_first_pass(HexaVal stmts) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(stmts))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal s = hexa_index_get(stmts, i);
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(s, "kind", &__hexa_type_checker_ic_125), hexa_str("FnDecl")))) {
            tc_register_fn(hexa_map_get_ic(s, "name", &__hexa_type_checker_ic_126), hexa_int(hexa_len(hexa_map_get_ic(s, "params", &__hexa_type_checker_ic_127))), annotation_to_type(hexa_map_get_ic(s, "ret_type", &__hexa_type_checker_ic_128)));
            tc_define(hexa_map_get_ic(s, "name", &__hexa_type_checker_ic_129), hexa_str("fn"));
            HexaVal fp_tparams = hexa_map_get_ic(s, "items", &__hexa_type_checker_ic_130);
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(fp_tparams, hexa_str(""))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(fp_tparams))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))))) {
                tc_register_generic_fn(hexa_map_get_ic(s, "name", &__hexa_type_checker_ic_131), fp_tparams);
            }
        }
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(s, "kind", &__hexa_type_checker_ic_132), hexa_str("StructDecl")))) {
            HexaVal fc = hexa_int(hexa_len(hexa_map_get_ic(s, "fields", &__hexa_type_checker_ic_133)));
            tc_register_struct(hexa_map_get_ic(s, "name", &__hexa_type_checker_ic_134), fc);
            HexaVal fi = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(fc); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                tc_register_struct_field(hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(s, "fields", &__hexa_type_checker_ic_135), fi), "name", &__hexa_type_checker_ic_136), hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(s, "fields", &__hexa_type_checker_ic_137), fi), "value", &__hexa_type_checker_ic_138));
                fi = hexa_add(fi, hexa_int(1));
            }
            HexaVal sp_tparams = hexa_map_get_ic(s, "items", &__hexa_type_checker_ic_139);
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(sp_tparams, hexa_str(""))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(sp_tparams))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))))) {
                tc_register_generic_struct(hexa_map_get_ic(s, "name", &__hexa_type_checker_ic_140), sp_tparams);
            }
            tc_define(hexa_map_get_ic(s, "name", &__hexa_type_checker_ic_141), hexa_str("type"));
        }
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(s, "kind", &__hexa_type_checker_ic_142), hexa_str("EnumDecl")))) {
            HexaVal vc = hexa_int(hexa_len(hexa_map_get_ic(s, "variants", &__hexa_type_checker_ic_143)));
            tc_register_enum(hexa_map_get_ic(s, "name", &__hexa_type_checker_ic_144), vc);
            HexaVal vi = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(vi); HexaVal __r=(vc); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                tc_register_enum_variant(hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(s, "variants", &__hexa_type_checker_ic_145), vi), "name", &__hexa_type_checker_ic_146));
                vi = hexa_add(vi, hexa_int(1));
            }
            tc_define(hexa_map_get_ic(s, "name", &__hexa_type_checker_ic_147), hexa_str("type"));
        }
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(s, "kind", &__hexa_type_checker_ic_148), hexa_str("TraitDecl")))) {
            tc_define(hexa_map_get_ic(s, "name", &__hexa_type_checker_ic_149), hexa_str("type"));
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_void();
}


HexaVal type_check(HexaVal stmts) {
    tc_errors = hexa_array_new();
    scope_names = hexa_array_new();
    scope_types = hexa_array_new();
    scope_depths = hexa_array_new();
    tc_depth = hexa_int(0);
    fn_names = hexa_array_new();
    fn_arities = hexa_array_new();
    fn_ret_types = hexa_array_new();
    tc_fn_cache_init();
    tc_scope_cache_init();
    struct_names = hexa_array_new();
    struct_field_counts = hexa_array_new();
    struct_field_offsets = hexa_array_new();
    struct_all_field_names = hexa_array_new();
    struct_all_field_types = hexa_array_new();
    enum_names = hexa_array_new();
    enum_variant_counts = hexa_array_new();
    enum_variant_offsets = hexa_array_new();
    enum_all_variant_names = hexa_array_new();
    current_fn_ret_type = hexa_str("unknown");
    current_fn_name = hexa_str("");
    generic_struct_names = hexa_array_new();
    generic_struct_param_counts = hexa_array_new();
    generic_struct_param_offsets = hexa_array_new();
    generic_all_param_names = hexa_array_new();
    generic_all_param_bounds = hexa_array_new();
    generic_fn_names = hexa_array_new();
    generic_fn_param_counts = hexa_array_new();
    generic_fn_param_offsets = hexa_array_new();
    generic_fn_all_param_names = hexa_array_new();
    generic_fn_all_param_bounds = hexa_array_new();
    tparam_names = hexa_array_new();
    tparam_bound = hexa_array_new();
    tc_register_builtins();
    tc_first_pass(stmts);
    tc_check_stmts(stmts);
    return tc_errors;
    return hexa_void();
}


HexaVal type_check_ok(HexaVal stmts) {
    HexaVal errors = type_check(stmts);
    return hexa_eq(hexa_int(hexa_len(errors)), hexa_int(0));
    return hexa_void();
}


HexaVal print_type_errors(HexaVal errors) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(errors))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal e = hexa_index_get(errors, i);
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(e, "name", &__hexa_type_checker_ic_150), hexa_str("")))))) {
            hexa_println(hexa_format_n(hexa_str("  TYPE ERROR [{}]: {}"), hexa_array_push(hexa_array_push(hexa_array_new(), hexa_map_get_ic(e, "name", &__hexa_type_checker_ic_151)), hexa_map_get_ic(e, "message", &__hexa_type_checker_ic_152))));
        } else {
            hexa_println(hexa_format_n(hexa_str("  TYPE ERROR: {}"), hexa_array_push(hexa_array_new(), hexa_map_get_ic(e, "message", &__hexa_type_checker_ic_153))));
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_void();
}


HexaVal type_errors_count(HexaVal errors) {
    return hexa_int(hexa_len(errors));
    return hexa_void();
}


HexaVal type_errors_has(HexaVal errors, HexaVal substr) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(errors))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal msg = hexa_map_get_ic(hexa_index_get(errors, i), "message", &__hexa_type_checker_ic_154);
        if (hexa_truthy(hexa_bool(hexa_str_contains(msg, substr)))) {
            return hexa_bool(1);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal type_warnings_count(HexaVal errors) {
    HexaVal count = hexa_int(0);
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(errors))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_bool(hexa_str_contains(hexa_map_get_ic(hexa_index_get(errors, i), "message", &__hexa_type_checker_ic_155), hexa_str("[warn]"))))) {
            count = hexa_add(count, hexa_int(1));
        }
        i = hexa_add(i, hexa_int(1));
    }
    return count;
    return hexa_void();
}


HexaVal mk(HexaVal kind, HexaVal name, HexaVal value, HexaVal op, HexaVal left, HexaVal right, HexaVal params, HexaVal body, HexaVal args, HexaVal fields, HexaVal variants, HexaVal arms, HexaVal ret_type) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", kind), "name", name), "value", value), "op", op), "left", left), "right", right), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", params), "body", body), "args", args), "fields", fields), "items", hexa_str("")), "variants", variants), "arms", arms), "iter_expr", hexa_str("")), "ret_type", ret_type), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal nd(HexaVal kind, HexaVal name) {
    return mk(kind, name, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal lit(HexaVal kind, HexaVal val) {
    return mk(kind, hexa_str(""), val, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal let_stmt(HexaVal name, HexaVal init) {
    return mk(hexa_str("LetStmt"), name, hexa_str(""), hexa_str(""), init, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal expr_stmt(HexaVal e) {
    return mk(hexa_str("ExprStmt"), hexa_str(""), hexa_str(""), hexa_str(""), e, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal ret_stmt(HexaVal e) {
    return mk(hexa_str("ReturnStmt"), hexa_str(""), hexa_str(""), hexa_str(""), e, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal fn_decl(HexaVal name, HexaVal params, HexaVal body, HexaVal ret) {
    return mk(hexa_str("FnDecl"), name, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), params, body, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), ret);
    return hexa_void();
}


HexaVal call_node(HexaVal callee, HexaVal args) {
    return mk(hexa_str("Call"), hexa_str(""), hexa_str(""), hexa_str(""), callee, hexa_str(""), hexa_str(""), hexa_str(""), args, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal field_node(HexaVal obj, HexaVal fname) {
    return mk(hexa_str("Field"), fname, hexa_str(""), hexa_str(""), obj, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal binop_node(HexaVal op, HexaVal left, HexaVal right) {
    return mk(hexa_str("BinOp"), hexa_str(""), hexa_str(""), op, left, right, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal struct_decl_node(HexaVal name, HexaVal fields) {
    return mk(hexa_str("StructDecl"), name, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), fields, hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal struct_field_node(HexaVal name, HexaVal typ) {
    return mk(hexa_str("StructField"), name, typ, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal struct_init_node(HexaVal name, HexaVal fields) {
    return mk(hexa_str("StructInit"), name, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), fields, hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal field_init_node(HexaVal name, HexaVal val) {
    return mk(hexa_str("FieldInit"), name, hexa_str(""), hexa_str(""), val, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal enum_decl_node(HexaVal name, HexaVal variants) {
    return mk(hexa_str("EnumDecl"), name, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), variants, hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal enum_variant_node(HexaVal name) {
    return nd(hexa_str("EnumVariant"), name);
    return hexa_void();
}


HexaVal match_expr_node(HexaVal scrutinee, HexaVal arms) {
    return mk(hexa_str("MatchExpr"), hexa_str(""), hexa_str(""), hexa_str(""), scrutinee, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), arms, hexa_str(""));
    return hexa_void();
}


HexaVal match_arm_node(HexaVal pattern, HexaVal body) {
    return mk(hexa_str("MatchArm"), hexa_str(""), hexa_str(""), hexa_str(""), pattern, hexa_str(""), hexa_str(""), body, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


HexaVal param_node(HexaVal name, HexaVal typ) {
    return mk(hexa_str("Param"), name, typ, hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""));
    return hexa_void();
}


int _type_checker_init(int argc, char** argv) {
    hexa_set_args(argc, argv);
    tc_errors = hexa_array_new();
    scope_names = hexa_array_new();
    scope_types = hexa_array_new();
    scope_depths = hexa_array_new();
    tc_depth = hexa_int(0);
    fn_names = hexa_array_new();
    fn_arities = hexa_array_new();
    fn_ret_types = hexa_array_new();
    fn_cache = hexa_array_new();
    scope_cache = hexa_array_new();
    struct_names = hexa_array_new();
    struct_field_counts = hexa_array_new();
    struct_field_offsets = hexa_array_new();
    struct_all_field_names = hexa_array_new();
    struct_all_field_types = hexa_array_new();
    enum_names = hexa_array_new();
    enum_variant_counts = hexa_array_new();
    enum_variant_offsets = hexa_array_new();
    enum_all_variant_names = hexa_array_new();
    current_fn_ret_type = hexa_str("unknown");
    current_fn_name = hexa_str("");
    generic_struct_names = hexa_array_new();
    generic_struct_param_counts = hexa_array_new();
    generic_struct_param_offsets = hexa_array_new();
    generic_all_param_names = hexa_array_new();
    generic_all_param_bounds = hexa_array_new();
    generic_fn_names = hexa_array_new();
    generic_fn_param_counts = hexa_array_new();
    generic_fn_param_offsets = hexa_array_new();
    generic_fn_all_param_names = hexa_array_new();
    generic_fn_all_param_bounds = hexa_array_new();
    tparam_names = hexa_array_new();
    tparam_bound = hexa_array_new();
    test_pass = hexa_int(0);
    s1 = hexa_array_new();
    s1 = hexa_array_push(s1, let_stmt(hexa_str("x"), lit(hexa_str("IntLit"), hexa_str("42"))));
    s1 = hexa_array_push(s1, let_stmt(hexa_str("y"), lit(hexa_str("StringLit"), hexa_str("hello"))));
    s1 = hexa_array_push(s1, let_stmt(hexa_str("z"), lit(hexa_str("BoolLit"), hexa_str("true"))));
    s1 = hexa_array_push(s1, let_stmt(hexa_str("w"), lit(hexa_str("FloatLit"), hexa_str("3.14"))));
    errs1 = type_check(s1);
    if (!hexa_truthy(hexa_eq(hexa_int(hexa_len(errs1)), hexa_int(0)))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    type_check(s1);
    if (!hexa_truthy(hexa_eq(tc_lookup(hexa_str("x")), hexa_str("int")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    if (!hexa_truthy(hexa_eq(tc_lookup(hexa_str("y")), hexa_str("string")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    if (!hexa_truthy(hexa_eq(tc_lookup(hexa_str("z")), hexa_str("bool")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    if (!hexa_truthy(hexa_eq(tc_lookup(hexa_str("w")), hexa_str("float")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 1 — type inference for literals (int/string/bool/float)"));
    p2 = hexa_array_new();
    p2 = hexa_array_push(p2, param_node(hexa_str("a"), hexa_str("int")));
    p2 = hexa_array_push(p2, param_node(hexa_str("b"), hexa_str("int")));
    body2 = hexa_array_new();
    body2 = hexa_array_push(body2, ret_stmt(binop_node(hexa_str("+"), nd(hexa_str("Ident"), hexa_str("a")), nd(hexa_str("Ident"), hexa_str("b")))));
    fd2 = fn_decl(hexa_str("add"), p2, body2, hexa_str("int"));
    args2a = hexa_array_new();
    args2a = hexa_array_push(args2a, lit(hexa_str("IntLit"), hexa_str("1")));
    args2a = hexa_array_push(args2a, lit(hexa_str("IntLit"), hexa_str("2")));
    s2a = hexa_array_new();
    s2a = hexa_array_push(s2a, fd2);
    s2a = hexa_array_push(s2a, expr_stmt(call_node(nd(hexa_str("Ident"), hexa_str("add")), args2a)));
    errs2a = type_check(s2a);
    if (!hexa_truthy(hexa_eq(hexa_int(hexa_len(errs2a)), hexa_int(0)))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 2a — correct arity (2 args) accepted"));
    args2b = hexa_array_new();
    args2b = hexa_array_push(args2b, lit(hexa_str("IntLit"), hexa_str("1")));
    args2b = hexa_array_push(args2b, lit(hexa_str("IntLit"), hexa_str("2")));
    args2b = hexa_array_push(args2b, lit(hexa_str("IntLit"), hexa_str("3")));
    s2b = hexa_array_new();
    s2b = hexa_array_push(s2b, fd2);
    s2b = hexa_array_push(s2b, expr_stmt(call_node(nd(hexa_str("Ident"), hexa_str("add")), args2b)));
    errs2b = type_check(s2b);
    if (!hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(errs2b))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    if (!hexa_truthy(type_errors_has(errs2b, hexa_str("expects 2 args")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 2b — wrong arity (3 args) detected"));
    sf3 = hexa_array_new();
    sf3 = hexa_array_push(sf3, struct_field_node(hexa_str("x"), hexa_str("int")));
    sf3 = hexa_array_push(sf3, struct_field_node(hexa_str("y"), hexa_str("int")));
    sd3 = struct_decl_node(hexa_str("Point"), sf3);
    fi3 = hexa_array_new();
    fi3 = hexa_array_push(fi3, field_init_node(hexa_str("x"), lit(hexa_str("IntLit"), hexa_str("10"))));
    fi3 = hexa_array_push(fi3, field_init_node(hexa_str("y"), lit(hexa_str("IntLit"), hexa_str("20"))));
    lp3 = let_stmt(hexa_str("p"), struct_init_node(hexa_str("Point"), fi3));
    fn3a = field_node(nd(hexa_str("Ident"), hexa_str("p")), hexa_str("x"));
    es3a = expr_stmt(fn3a);
    s3a = hexa_array_new();
    s3a = hexa_array_push(s3a, sd3);
    s3a = hexa_array_push(s3a, lp3);
    s3a = hexa_array_push(s3a, es3a);
    errs3a = type_check(s3a);
    if (!hexa_truthy(hexa_eq(hexa_int(hexa_len(errs3a)), hexa_int(0)))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 3a — valid struct field access (Point.x)"));
    fn3b = field_node(nd(hexa_str("Ident"), hexa_str("p")), hexa_str("z"));
    es3b = expr_stmt(fn3b);
    s3b = hexa_array_new();
    s3b = hexa_array_push(s3b, sd3);
    s3b = hexa_array_push(s3b, lp3);
    s3b = hexa_array_push(s3b, es3b);
    errs3b = type_check(s3b);
    if (!hexa_truthy(type_errors_has(errs3b, hexa_str("has no field 'z'")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 3b — invalid struct field 'z' detected"));
    body4 = hexa_array_new();
    body4 = hexa_array_push(body4, ret_stmt(lit(hexa_str("StringLit"), hexa_str("oops"))));
    s4 = hexa_array_new();
    s4 = hexa_array_push(s4, fn_decl(hexa_str("get_num"), hexa_array_new(), body4, hexa_str("int")));
    errs4 = type_check(s4);
    if (!hexa_truthy(type_errors_has(errs4, hexa_str("Return type mismatch")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 4 — return type mismatch (string vs int) detected"));
    ev5 = hexa_array_new();
    ev5 = hexa_array_push(ev5, enum_variant_node(hexa_str("Red")));
    ev5 = hexa_array_push(ev5, enum_variant_node(hexa_str("Green")));
    ev5 = hexa_array_push(ev5, enum_variant_node(hexa_str("Blue")));
    ed5 = enum_decl_node(hexa_str("Color"), ev5);
    lc5 = let_stmt(hexa_str("c"), nd(hexa_str("Ident"), hexa_str("c")));
    ab5a = hexa_array_new();
    ab5a = hexa_array_push(ab5a, expr_stmt(lit(hexa_str("IntLit"), hexa_str("0"))));
    arms5a = hexa_array_new();
    arms5a = hexa_array_push(arms5a, match_arm_node(nd(hexa_str("Wildcard"), hexa_str("_")), ab5a));
    s5a = hexa_array_new();
    s5a = hexa_array_push(s5a, ed5);
    s5a = hexa_array_push(s5a, mk(hexa_str("LetMutStmt"), hexa_str("c"), hexa_str("Color"), hexa_str(""), lit(hexa_str("StringLit"), hexa_str("Red")), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str(""), hexa_str("")));
    s5a = hexa_array_push(s5a, expr_stmt(match_expr_node(nd(hexa_str("Ident"), hexa_str("c")), arms5a)));
    errs5a = type_check(s5a);
    w5a = type_warnings_count(errs5a);
    if (!hexa_truthy(hexa_eq(w5a, hexa_int(0)))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 5a — match with wildcard (no exhaustiveness warning)"));
    ab5b = hexa_array_new();
    ab5b = hexa_array_push(ab5b, expr_stmt(lit(hexa_str("IntLit"), hexa_str("1"))));
    arms5b = hexa_array_new();
    arms5b = hexa_array_push(arms5b, match_arm_node(lit(hexa_str("IntLit"), hexa_str("0")), ab5b));
    s5b = hexa_array_new();
    s5b = hexa_array_push(s5b, expr_stmt(match_expr_node(nd(hexa_str("Ident"), hexa_str("unknown_var")), arms5b)));
    errs5b = type_check(s5b);
    w5b = type_warnings_count(errs5b);
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_add(hexa_add(hexa_str("PASS: Test 5b — match without wildcard (warnings: "), hexa_to_string(w5b)), hexa_str(")")));
    s6 = hexa_array_new();
    s6 = hexa_array_push(s6, expr_stmt(nd(hexa_str("Ident"), hexa_str("undefined_a"))));
    s6 = hexa_array_push(s6, expr_stmt(nd(hexa_str("Ident"), hexa_str("undefined_b"))));
    s6 = hexa_array_push(s6, expr_stmt(nd(hexa_str("Ident"), hexa_str("undefined_c"))));
    errs6 = type_check(s6);
    if (!hexa_truthy(hexa_eq(hexa_int(hexa_len(errs6)), hexa_int(3)))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    if (!hexa_truthy(type_errors_has(errs6, hexa_str("undefined_a")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    if (!hexa_truthy(type_errors_has(errs6, hexa_str("undefined_b")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    if (!hexa_truthy(type_errors_has(errs6, hexa_str("undefined_c")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 6 — error accumulation (3 errors collected, not stopped at first)"));
    fi7 = hexa_array_new();
    fi7 = hexa_array_push(fi7, field_init_node(hexa_str("x"), lit(hexa_str("IntLit"), hexa_str("10"))));
    s7 = hexa_array_new();
    s7 = hexa_array_push(s7, sd3);
    s7 = hexa_array_push(s7, let_stmt(hexa_str("q"), struct_init_node(hexa_str("Point"), fi7)));
    errs7 = type_check(s7);
    if (!hexa_truthy(type_errors_has(errs7, hexa_str("has 2 fields")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 7 — struct init field count mismatch detected"));
    body8 = hexa_array_new();
    body8 = hexa_array_push(body8, ret_stmt(lit(hexa_str("IntLit"), hexa_str("42"))));
    s8 = hexa_array_new();
    s8 = hexa_array_push(s8, fn_decl(hexa_str("get_num2"), hexa_array_new(), body8, hexa_str("int")));
    errs8 = type_check(s8);
    if (!hexa_truthy(hexa_eq(hexa_int(hexa_len(errs8)), hexa_int(0)))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 8 — correct return type (int -> int) accepted"));
    fi9 = hexa_array_new();
    fi9 = hexa_array_push(fi9, field_init_node(hexa_str("x"), lit(hexa_str("StringLit"), hexa_str("bad"))));
    fi9 = hexa_array_push(fi9, field_init_node(hexa_str("y"), lit(hexa_str("IntLit"), hexa_str("20"))));
    s9 = hexa_array_new();
    s9 = hexa_array_push(s9, sd3);
    s9 = hexa_array_push(s9, let_stmt(hexa_str("r"), struct_init_node(hexa_str("Point"), fi9)));
    errs9 = type_check(s9);
    if (!hexa_truthy(type_errors_has(errs9, hexa_str("Field type mismatch")))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 9 — struct field type mismatch (string into int field)"));
    inner_body = hexa_array_new();
    inner_body = hexa_array_push(inner_body, ret_stmt(lit(hexa_str("IntLit"), hexa_str("1"))));
    outer_body = hexa_array_new();
    outer_body = hexa_array_push(outer_body, fn_decl(hexa_str("inner"), hexa_array_new(), inner_body, hexa_str("int")));
    outer_body = hexa_array_push(outer_body, ret_stmt(lit(hexa_str("StringLit"), hexa_str("hello"))));
    s10 = hexa_array_new();
    s10 = hexa_array_push(s10, fn_decl(hexa_str("outer"), hexa_array_new(), outer_body, hexa_str("string")));
    errs10 = type_check(s10);
    if (!hexa_truthy(hexa_eq(hexa_int(hexa_len(errs10)), hexa_int(0)))) { fprintf(stderr, "assertion failed\n"); exit(1); }
    test_pass = hexa_add(test_pass, hexa_int(1));
    hexa_println(hexa_str("PASS: Test 10 — nested fn return type isolation (inner:int, outer:string)"));
    hexa_println(hexa_str(""));
    hexa_println(hexa_add(hexa_add(hexa_str("=== self/type_checker.hexa — "), hexa_to_string(test_pass)), hexa_str(" tests passed ===")));
    return 0;
}

// === codegen_c2 ===


HexaVal gen2_fn_forward(HexaVal node);
HexaVal gen2_fn_decl(HexaVal node);
HexaVal gen2_stmt_stack_alloc(HexaVal node, HexaVal depth);
HexaVal gen2_extern_wrapper(HexaVal node);
HexaVal gen2_indent(HexaVal n);
HexaVal _gen2_has_decl(HexaVal name);
HexaVal _gen2_collect_lets(HexaVal stmts, HexaVal names);
HexaVal gen2_stmt(HexaVal node, HexaVal depth);
HexaVal gen2_expr(HexaVal node);
HexaVal gen2_struct_forward(HexaVal node);
HexaVal gen2_struct_decl(HexaVal node);
HexaVal gen2_enum_decl(HexaVal node);
HexaVal gen2_min_bits(HexaVal count);
HexaVal gen2_hex_mask(HexaVal bits);
HexaVal gen2_match_stmt(HexaVal node, HexaVal depth);
HexaVal gen2_match_cond(HexaVal pat, HexaVal scrutinee_var);
HexaVal gen2_match_expr(HexaVal node);
HexaVal gen2_match_ternary(HexaVal arms, HexaVal scrutinee_c, HexaVal idx);
HexaVal gen2_arm_value(HexaVal body);
HexaVal _method_registry_lookup(HexaVal name);
HexaVal gen2_impl_block(HexaVal node);
HexaVal _lookup_comptime_const(HexaVal name);
HexaVal comptime_eval(HexaVal node);
HexaVal _register_comptime_const(HexaVal name, HexaVal value_node);
HexaVal _is_known_fn_global(HexaVal name);
HexaVal gen2_lambda_expr(HexaVal node);

HexaVal _gen2_declared_names;
HexaVal _method_registry;
HexaVal _lambda_counter;
HexaVal _lambda_def_parts;
HexaVal _ic_counter;
HexaVal _ic_def_parts;
HexaVal _comptime_const_names;
HexaVal _comptime_const_nodes;
HexaVal _known_fn_globals;
HexaVal _known_nonlocal_names;

static HexaIC __hexa_codegen_c2_ic_0 = {0};
static HexaIC __hexa_codegen_c2_ic_1 = {0};
static HexaIC __hexa_codegen_c2_ic_2 = {0};
static HexaIC __hexa_codegen_c2_ic_3 = {0};
static HexaIC __hexa_codegen_c2_ic_4 = {0};
static HexaIC __hexa_codegen_c2_ic_5 = {0};
static HexaIC __hexa_codegen_c2_ic_6 = {0};
static HexaIC __hexa_codegen_c2_ic_7 = {0};
static HexaIC __hexa_codegen_c2_ic_8 = {0};
static HexaIC __hexa_codegen_c2_ic_9 = {0};
static HexaIC __hexa_codegen_c2_ic_10 = {0};
static HexaIC __hexa_codegen_c2_ic_11 = {0};
static HexaIC __hexa_codegen_c2_ic_12 = {0};
static HexaIC __hexa_codegen_c2_ic_13 = {0};
static HexaIC __hexa_codegen_c2_ic_14 = {0};
static HexaIC __hexa_codegen_c2_ic_15 = {0};
static HexaIC __hexa_codegen_c2_ic_16 = {0};
static HexaIC __hexa_codegen_c2_ic_17 = {0};
static HexaIC __hexa_codegen_c2_ic_18 = {0};
static HexaIC __hexa_codegen_c2_ic_19 = {0};
static HexaIC __hexa_codegen_c2_ic_20 = {0};
static HexaIC __hexa_codegen_c2_ic_21 = {0};
static HexaIC __hexa_codegen_c2_ic_22 = {0};
static HexaIC __hexa_codegen_c2_ic_23 = {0};
static HexaIC __hexa_codegen_c2_ic_24 = {0};
static HexaIC __hexa_codegen_c2_ic_25 = {0};
static HexaIC __hexa_codegen_c2_ic_26 = {0};
static HexaIC __hexa_codegen_c2_ic_27 = {0};
static HexaIC __hexa_codegen_c2_ic_28 = {0};
static HexaIC __hexa_codegen_c2_ic_29 = {0};
static HexaIC __hexa_codegen_c2_ic_30 = {0};
static HexaIC __hexa_codegen_c2_ic_31 = {0};
static HexaIC __hexa_codegen_c2_ic_32 = {0};
static HexaIC __hexa_codegen_c2_ic_33 = {0};
static HexaIC __hexa_codegen_c2_ic_34 = {0};
static HexaIC __hexa_codegen_c2_ic_35 = {0};
static HexaIC __hexa_codegen_c2_ic_36 = {0};
static HexaIC __hexa_codegen_c2_ic_37 = {0};
static HexaIC __hexa_codegen_c2_ic_38 = {0};
static HexaIC __hexa_codegen_c2_ic_39 = {0};
static HexaIC __hexa_codegen_c2_ic_40 = {0};
static HexaIC __hexa_codegen_c2_ic_41 = {0};
static HexaIC __hexa_codegen_c2_ic_42 = {0};
static HexaIC __hexa_codegen_c2_ic_43 = {0};
static HexaIC __hexa_codegen_c2_ic_44 = {0};
static HexaIC __hexa_codegen_c2_ic_45 = {0};
static HexaIC __hexa_codegen_c2_ic_46 = {0};
static HexaIC __hexa_codegen_c2_ic_47 = {0};
static HexaIC __hexa_codegen_c2_ic_48 = {0};
static HexaIC __hexa_codegen_c2_ic_49 = {0};
static HexaIC __hexa_codegen_c2_ic_50 = {0};
static HexaIC __hexa_codegen_c2_ic_51 = {0};
static HexaIC __hexa_codegen_c2_ic_52 = {0};
static HexaIC __hexa_codegen_c2_ic_53 = {0};
static HexaIC __hexa_codegen_c2_ic_54 = {0};
static HexaIC __hexa_codegen_c2_ic_55 = {0};
static HexaIC __hexa_codegen_c2_ic_56 = {0};
static HexaIC __hexa_codegen_c2_ic_57 = {0};
static HexaIC __hexa_codegen_c2_ic_58 = {0};
static HexaIC __hexa_codegen_c2_ic_59 = {0};
static HexaIC __hexa_codegen_c2_ic_60 = {0};
static HexaIC __hexa_codegen_c2_ic_61 = {0};
static HexaIC __hexa_codegen_c2_ic_62 = {0};
static HexaIC __hexa_codegen_c2_ic_63 = {0};
static HexaIC __hexa_codegen_c2_ic_64 = {0};
static HexaIC __hexa_codegen_c2_ic_65 = {0};
static HexaIC __hexa_codegen_c2_ic_66 = {0};
static HexaIC __hexa_codegen_c2_ic_67 = {0};
static HexaIC __hexa_codegen_c2_ic_68 = {0};
static HexaIC __hexa_codegen_c2_ic_69 = {0};
static HexaIC __hexa_codegen_c2_ic_70 = {0};
static HexaIC __hexa_codegen_c2_ic_71 = {0};
static HexaIC __hexa_codegen_c2_ic_72 = {0};
static HexaIC __hexa_codegen_c2_ic_73 = {0};
static HexaIC __hexa_codegen_c2_ic_74 = {0};
static HexaIC __hexa_codegen_c2_ic_75 = {0};
static HexaIC __hexa_codegen_c2_ic_76 = {0};
static HexaIC __hexa_codegen_c2_ic_77 = {0};
static HexaIC __hexa_codegen_c2_ic_78 = {0};
static HexaIC __hexa_codegen_c2_ic_79 = {0};
static HexaIC __hexa_codegen_c2_ic_80 = {0};
static HexaIC __hexa_codegen_c2_ic_81 = {0};
static HexaIC __hexa_codegen_c2_ic_82 = {0};
static HexaIC __hexa_codegen_c2_ic_83 = {0};
static HexaIC __hexa_codegen_c2_ic_84 = {0};
static HexaIC __hexa_codegen_c2_ic_85 = {0};
static HexaIC __hexa_codegen_c2_ic_86 = {0};
static HexaIC __hexa_codegen_c2_ic_87 = {0};
static HexaIC __hexa_codegen_c2_ic_88 = {0};
static HexaIC __hexa_codegen_c2_ic_89 = {0};
static HexaIC __hexa_codegen_c2_ic_90 = {0};
static HexaIC __hexa_codegen_c2_ic_91 = {0};
static HexaIC __hexa_codegen_c2_ic_92 = {0};
static HexaIC __hexa_codegen_c2_ic_93 = {0};
static HexaIC __hexa_codegen_c2_ic_94 = {0};
static HexaIC __hexa_codegen_c2_ic_95 = {0};
static HexaIC __hexa_codegen_c2_ic_96 = {0};
static HexaIC __hexa_codegen_c2_ic_97 = {0};
static HexaIC __hexa_codegen_c2_ic_98 = {0};
static HexaIC __hexa_codegen_c2_ic_99 = {0};
static HexaIC __hexa_codegen_c2_ic_100 = {0};
static HexaIC __hexa_codegen_c2_ic_101 = {0};
static HexaIC __hexa_codegen_c2_ic_102 = {0};
static HexaIC __hexa_codegen_c2_ic_103 = {0};
static HexaIC __hexa_codegen_c2_ic_104 = {0};
static HexaIC __hexa_codegen_c2_ic_105 = {0};
static HexaIC __hexa_codegen_c2_ic_106 = {0};
static HexaIC __hexa_codegen_c2_ic_107 = {0};
static HexaIC __hexa_codegen_c2_ic_108 = {0};
static HexaIC __hexa_codegen_c2_ic_109 = {0};
static HexaIC __hexa_codegen_c2_ic_110 = {0};
static HexaIC __hexa_codegen_c2_ic_111 = {0};
static HexaIC __hexa_codegen_c2_ic_112 = {0};
static HexaIC __hexa_codegen_c2_ic_113 = {0};
static HexaIC __hexa_codegen_c2_ic_114 = {0};
static HexaIC __hexa_codegen_c2_ic_115 = {0};
static HexaIC __hexa_codegen_c2_ic_116 = {0};
static HexaIC __hexa_codegen_c2_ic_117 = {0};
static HexaIC __hexa_codegen_c2_ic_118 = {0};
static HexaIC __hexa_codegen_c2_ic_119 = {0};
static HexaIC __hexa_codegen_c2_ic_120 = {0};
static HexaIC __hexa_codegen_c2_ic_121 = {0};
static HexaIC __hexa_codegen_c2_ic_122 = {0};
static HexaIC __hexa_codegen_c2_ic_123 = {0};
static HexaIC __hexa_codegen_c2_ic_124 = {0};
static HexaIC __hexa_codegen_c2_ic_125 = {0};
static HexaIC __hexa_codegen_c2_ic_126 = {0};
static HexaIC __hexa_codegen_c2_ic_127 = {0};
static HexaIC __hexa_codegen_c2_ic_128 = {0};
static HexaIC __hexa_codegen_c2_ic_129 = {0};
static HexaIC __hexa_codegen_c2_ic_130 = {0};
static HexaIC __hexa_codegen_c2_ic_131 = {0};
static HexaIC __hexa_codegen_c2_ic_132 = {0};
static HexaIC __hexa_codegen_c2_ic_133 = {0};
static HexaIC __hexa_codegen_c2_ic_134 = {0};
static HexaIC __hexa_codegen_c2_ic_135 = {0};
static HexaIC __hexa_codegen_c2_ic_136 = {0};
static HexaIC __hexa_codegen_c2_ic_137 = {0};
static HexaIC __hexa_codegen_c2_ic_138 = {0};
static HexaIC __hexa_codegen_c2_ic_139 = {0};
static HexaIC __hexa_codegen_c2_ic_140 = {0};
static HexaIC __hexa_codegen_c2_ic_141 = {0};
static HexaIC __hexa_codegen_c2_ic_142 = {0};
static HexaIC __hexa_codegen_c2_ic_143 = {0};
static HexaIC __hexa_codegen_c2_ic_144 = {0};
static HexaIC __hexa_codegen_c2_ic_145 = {0};
static HexaIC __hexa_codegen_c2_ic_146 = {0};
static HexaIC __hexa_codegen_c2_ic_147 = {0};
static HexaIC __hexa_codegen_c2_ic_148 = {0};
static HexaIC __hexa_codegen_c2_ic_149 = {0};
static HexaIC __hexa_codegen_c2_ic_150 = {0};
static HexaIC __hexa_codegen_c2_ic_151 = {0};
static HexaIC __hexa_codegen_c2_ic_152 = {0};
static HexaIC __hexa_codegen_c2_ic_153 = {0};
static HexaIC __hexa_codegen_c2_ic_154 = {0};
static HexaIC __hexa_codegen_c2_ic_155 = {0};
static HexaIC __hexa_codegen_c2_ic_156 = {0};
static HexaIC __hexa_codegen_c2_ic_157 = {0};
static HexaIC __hexa_codegen_c2_ic_158 = {0};
static HexaIC __hexa_codegen_c2_ic_159 = {0};
static HexaIC __hexa_codegen_c2_ic_160 = {0};
static HexaIC __hexa_codegen_c2_ic_161 = {0};
static HexaIC __hexa_codegen_c2_ic_162 = {0};
static HexaIC __hexa_codegen_c2_ic_163 = {0};
static HexaIC __hexa_codegen_c2_ic_164 = {0};
static HexaIC __hexa_codegen_c2_ic_165 = {0};
static HexaIC __hexa_codegen_c2_ic_166 = {0};
static HexaIC __hexa_codegen_c2_ic_167 = {0};
static HexaIC __hexa_codegen_c2_ic_168 = {0};
static HexaIC __hexa_codegen_c2_ic_169 = {0};
static HexaIC __hexa_codegen_c2_ic_170 = {0};
static HexaIC __hexa_codegen_c2_ic_171 = {0};
static HexaIC __hexa_codegen_c2_ic_172 = {0};
static HexaIC __hexa_codegen_c2_ic_173 = {0};
static HexaIC __hexa_codegen_c2_ic_174 = {0};
static HexaIC __hexa_codegen_c2_ic_175 = {0};
static HexaIC __hexa_codegen_c2_ic_176 = {0};
static HexaIC __hexa_codegen_c2_ic_177 = {0};
static HexaIC __hexa_codegen_c2_ic_178 = {0};
static HexaIC __hexa_codegen_c2_ic_179 = {0};
static HexaIC __hexa_codegen_c2_ic_180 = {0};
static HexaIC __hexa_codegen_c2_ic_181 = {0};
static HexaIC __hexa_codegen_c2_ic_182 = {0};
static HexaIC __hexa_codegen_c2_ic_183 = {0};
static HexaIC __hexa_codegen_c2_ic_184 = {0};
static HexaIC __hexa_codegen_c2_ic_185 = {0};
static HexaIC __hexa_codegen_c2_ic_186 = {0};
static HexaIC __hexa_codegen_c2_ic_187 = {0};
static HexaIC __hexa_codegen_c2_ic_188 = {0};
static HexaIC __hexa_codegen_c2_ic_189 = {0};
static HexaIC __hexa_codegen_c2_ic_190 = {0};
static HexaIC __hexa_codegen_c2_ic_191 = {0};
static HexaIC __hexa_codegen_c2_ic_192 = {0};
static HexaIC __hexa_codegen_c2_ic_193 = {0};
static HexaIC __hexa_codegen_c2_ic_194 = {0};
static HexaIC __hexa_codegen_c2_ic_195 = {0};
static HexaIC __hexa_codegen_c2_ic_196 = {0};
static HexaIC __hexa_codegen_c2_ic_197 = {0};
static HexaIC __hexa_codegen_c2_ic_198 = {0};
static HexaIC __hexa_codegen_c2_ic_199 = {0};
static HexaIC __hexa_codegen_c2_ic_200 = {0};
static HexaIC __hexa_codegen_c2_ic_201 = {0};
static HexaIC __hexa_codegen_c2_ic_202 = {0};
static HexaIC __hexa_codegen_c2_ic_203 = {0};
static HexaIC __hexa_codegen_c2_ic_204 = {0};
static HexaIC __hexa_codegen_c2_ic_205 = {0};
static HexaIC __hexa_codegen_c2_ic_206 = {0};
static HexaIC __hexa_codegen_c2_ic_207 = {0};
static HexaIC __hexa_codegen_c2_ic_208 = {0};
static HexaIC __hexa_codegen_c2_ic_209 = {0};
static HexaIC __hexa_codegen_c2_ic_210 = {0};
static HexaIC __hexa_codegen_c2_ic_211 = {0};
static HexaIC __hexa_codegen_c2_ic_212 = {0};
static HexaIC __hexa_codegen_c2_ic_213 = {0};
static HexaIC __hexa_codegen_c2_ic_214 = {0};
static HexaIC __hexa_codegen_c2_ic_215 = {0};
static HexaIC __hexa_codegen_c2_ic_216 = {0};
static HexaIC __hexa_codegen_c2_ic_217 = {0};
static HexaIC __hexa_codegen_c2_ic_218 = {0};
static HexaIC __hexa_codegen_c2_ic_219 = {0};
static HexaIC __hexa_codegen_c2_ic_220 = {0};
static HexaIC __hexa_codegen_c2_ic_221 = {0};
static HexaIC __hexa_codegen_c2_ic_222 = {0};
static HexaIC __hexa_codegen_c2_ic_223 = {0};
static HexaIC __hexa_codegen_c2_ic_224 = {0};
static HexaIC __hexa_codegen_c2_ic_225 = {0};
static HexaIC __hexa_codegen_c2_ic_226 = {0};
static HexaIC __hexa_codegen_c2_ic_227 = {0};
static HexaIC __hexa_codegen_c2_ic_228 = {0};
static HexaIC __hexa_codegen_c2_ic_229 = {0};
static HexaIC __hexa_codegen_c2_ic_230 = {0};
static HexaIC __hexa_codegen_c2_ic_231 = {0};
static HexaIC __hexa_codegen_c2_ic_232 = {0};
static HexaIC __hexa_codegen_c2_ic_233 = {0};
static HexaIC __hexa_codegen_c2_ic_234 = {0};
static HexaIC __hexa_codegen_c2_ic_235 = {0};
static HexaIC __hexa_codegen_c2_ic_236 = {0};
static HexaIC __hexa_codegen_c2_ic_237 = {0};
static HexaIC __hexa_codegen_c2_ic_238 = {0};
static HexaIC __hexa_codegen_c2_ic_239 = {0};
static HexaIC __hexa_codegen_c2_ic_240 = {0};
static HexaIC __hexa_codegen_c2_ic_241 = {0};
static HexaIC __hexa_codegen_c2_ic_242 = {0};
static HexaIC __hexa_codegen_c2_ic_243 = {0};
static HexaIC __hexa_codegen_c2_ic_244 = {0};
static HexaIC __hexa_codegen_c2_ic_245 = {0};
static HexaIC __hexa_codegen_c2_ic_246 = {0};
static HexaIC __hexa_codegen_c2_ic_247 = {0};
static HexaIC __hexa_codegen_c2_ic_248 = {0};
static HexaIC __hexa_codegen_c2_ic_249 = {0};
static HexaIC __hexa_codegen_c2_ic_250 = {0};
static HexaIC __hexa_codegen_c2_ic_251 = {0};
static HexaIC __hexa_codegen_c2_ic_252 = {0};
static HexaIC __hexa_codegen_c2_ic_253 = {0};
static HexaIC __hexa_codegen_c2_ic_254 = {0};
static HexaIC __hexa_codegen_c2_ic_255 = {0};
static HexaIC __hexa_codegen_c2_ic_256 = {0};
static HexaIC __hexa_codegen_c2_ic_257 = {0};
static HexaIC __hexa_codegen_c2_ic_258 = {0};
static HexaIC __hexa_codegen_c2_ic_259 = {0};
static HexaIC __hexa_codegen_c2_ic_260 = {0};
static HexaIC __hexa_codegen_c2_ic_261 = {0};
static HexaIC __hexa_codegen_c2_ic_262 = {0};
static HexaIC __hexa_codegen_c2_ic_263 = {0};
static HexaIC __hexa_codegen_c2_ic_264 = {0};
static HexaIC __hexa_codegen_c2_ic_265 = {0};
static HexaIC __hexa_codegen_c2_ic_266 = {0};
static HexaIC __hexa_codegen_c2_ic_267 = {0};
static HexaIC __hexa_codegen_c2_ic_268 = {0};
static HexaIC __hexa_codegen_c2_ic_269 = {0};
static HexaIC __hexa_codegen_c2_ic_270 = {0};
static HexaIC __hexa_codegen_c2_ic_271 = {0};
static HexaIC __hexa_codegen_c2_ic_272 = {0};
static HexaIC __hexa_codegen_c2_ic_273 = {0};
static HexaIC __hexa_codegen_c2_ic_274 = {0};
static HexaIC __hexa_codegen_c2_ic_275 = {0};
static HexaIC __hexa_codegen_c2_ic_276 = {0};
static HexaIC __hexa_codegen_c2_ic_277 = {0};
static HexaIC __hexa_codegen_c2_ic_278 = {0};
static HexaIC __hexa_codegen_c2_ic_279 = {0};
static HexaIC __hexa_codegen_c2_ic_280 = {0};
static HexaIC __hexa_codegen_c2_ic_281 = {0};
static HexaIC __hexa_codegen_c2_ic_282 = {0};
static HexaIC __hexa_codegen_c2_ic_283 = {0};
static HexaIC __hexa_codegen_c2_ic_284 = {0};
static HexaIC __hexa_codegen_c2_ic_285 = {0};
static HexaIC __hexa_codegen_c2_ic_286 = {0};
static HexaIC __hexa_codegen_c2_ic_287 = {0};
static HexaIC __hexa_codegen_c2_ic_288 = {0};
static HexaIC __hexa_codegen_c2_ic_289 = {0};
static HexaIC __hexa_codegen_c2_ic_290 = {0};
static HexaIC __hexa_codegen_c2_ic_291 = {0};
static HexaIC __hexa_codegen_c2_ic_292 = {0};
static HexaIC __hexa_codegen_c2_ic_293 = {0};
static HexaIC __hexa_codegen_c2_ic_294 = {0};
static HexaIC __hexa_codegen_c2_ic_295 = {0};
static HexaIC __hexa_codegen_c2_ic_296 = {0};
static HexaIC __hexa_codegen_c2_ic_297 = {0};
static HexaIC __hexa_codegen_c2_ic_298 = {0};
static HexaIC __hexa_codegen_c2_ic_299 = {0};
static HexaIC __hexa_codegen_c2_ic_300 = {0};
static HexaIC __hexa_codegen_c2_ic_301 = {0};
static HexaIC __hexa_codegen_c2_ic_302 = {0};
static HexaIC __hexa_codegen_c2_ic_303 = {0};
static HexaIC __hexa_codegen_c2_ic_304 = {0};
static HexaIC __hexa_codegen_c2_ic_305 = {0};
static HexaIC __hexa_codegen_c2_ic_306 = {0};
static HexaIC __hexa_codegen_c2_ic_307 = {0};
static HexaIC __hexa_codegen_c2_ic_308 = {0};
static HexaIC __hexa_codegen_c2_ic_309 = {0};
static HexaIC __hexa_codegen_c2_ic_310 = {0};
static HexaIC __hexa_codegen_c2_ic_311 = {0};
static HexaIC __hexa_codegen_c2_ic_312 = {0};
static HexaIC __hexa_codegen_c2_ic_313 = {0};
static HexaIC __hexa_codegen_c2_ic_314 = {0};
static HexaIC __hexa_codegen_c2_ic_315 = {0};
static HexaIC __hexa_codegen_c2_ic_316 = {0};
static HexaIC __hexa_codegen_c2_ic_317 = {0};
static HexaIC __hexa_codegen_c2_ic_318 = {0};
static HexaIC __hexa_codegen_c2_ic_319 = {0};
static HexaIC __hexa_codegen_c2_ic_320 = {0};
static HexaIC __hexa_codegen_c2_ic_321 = {0};
static HexaIC __hexa_codegen_c2_ic_322 = {0};
static HexaIC __hexa_codegen_c2_ic_323 = {0};
static HexaIC __hexa_codegen_c2_ic_324 = {0};
static HexaIC __hexa_codegen_c2_ic_325 = {0};
static HexaIC __hexa_codegen_c2_ic_326 = {0};
static HexaIC __hexa_codegen_c2_ic_327 = {0};
static HexaIC __hexa_codegen_c2_ic_328 = {0};
static HexaIC __hexa_codegen_c2_ic_329 = {0};
static HexaIC __hexa_codegen_c2_ic_330 = {0};
static HexaIC __hexa_codegen_c2_ic_331 = {0};
static HexaIC __hexa_codegen_c2_ic_332 = {0};
static HexaIC __hexa_codegen_c2_ic_333 = {0};
static HexaIC __hexa_codegen_c2_ic_334 = {0};
static HexaIC __hexa_codegen_c2_ic_335 = {0};
static HexaIC __hexa_codegen_c2_ic_336 = {0};
static HexaIC __hexa_codegen_c2_ic_337 = {0};
static HexaIC __hexa_codegen_c2_ic_338 = {0};
static HexaIC __hexa_codegen_c2_ic_339 = {0};
static HexaIC __hexa_codegen_c2_ic_340 = {0};
static HexaIC __hexa_codegen_c2_ic_341 = {0};
static HexaIC __hexa_codegen_c2_ic_342 = {0};
static HexaIC __hexa_codegen_c2_ic_343 = {0};
static HexaIC __hexa_codegen_c2_ic_344 = {0};
static HexaIC __hexa_codegen_c2_ic_345 = {0};
static HexaIC __hexa_codegen_c2_ic_346 = {0};
static HexaIC __hexa_codegen_c2_ic_347 = {0};
static HexaIC __hexa_codegen_c2_ic_348 = {0};
static HexaIC __hexa_codegen_c2_ic_349 = {0};
static HexaIC __hexa_codegen_c2_ic_350 = {0};
static HexaIC __hexa_codegen_c2_ic_351 = {0};
static HexaIC __hexa_codegen_c2_ic_352 = {0};
static HexaIC __hexa_codegen_c2_ic_353 = {0};
static HexaIC __hexa_codegen_c2_ic_354 = {0};
static HexaIC __hexa_codegen_c2_ic_355 = {0};
static HexaIC __hexa_codegen_c2_ic_356 = {0};
static HexaIC __hexa_codegen_c2_ic_357 = {0};
static HexaIC __hexa_codegen_c2_ic_358 = {0};
static HexaIC __hexa_codegen_c2_ic_359 = {0};
static HexaIC __hexa_codegen_c2_ic_360 = {0};
static HexaIC __hexa_codegen_c2_ic_361 = {0};
static HexaIC __hexa_codegen_c2_ic_362 = {0};
static HexaIC __hexa_codegen_c2_ic_363 = {0};
static HexaIC __hexa_codegen_c2_ic_364 = {0};
static HexaIC __hexa_codegen_c2_ic_365 = {0};
static HexaIC __hexa_codegen_c2_ic_366 = {0};
static HexaIC __hexa_codegen_c2_ic_367 = {0};
static HexaIC __hexa_codegen_c2_ic_368 = {0};
static HexaIC __hexa_codegen_c2_ic_369 = {0};
static HexaIC __hexa_codegen_c2_ic_370 = {0};
static HexaIC __hexa_codegen_c2_ic_371 = {0};
static HexaIC __hexa_codegen_c2_ic_372 = {0};
static HexaIC __hexa_codegen_c2_ic_373 = {0};
static HexaIC __hexa_codegen_c2_ic_374 = {0};
static HexaIC __hexa_codegen_c2_ic_375 = {0};
static HexaIC __hexa_codegen_c2_ic_376 = {0};
static HexaIC __hexa_codegen_c2_ic_377 = {0};
static HexaIC __hexa_codegen_c2_ic_378 = {0};
static HexaIC __hexa_codegen_c2_ic_379 = {0};
static HexaIC __hexa_codegen_c2_ic_380 = {0};
static HexaIC __hexa_codegen_c2_ic_381 = {0};
static HexaIC __hexa_codegen_c2_ic_382 = {0};
static HexaIC __hexa_codegen_c2_ic_383 = {0};
static HexaIC __hexa_codegen_c2_ic_384 = {0};
static HexaIC __hexa_codegen_c2_ic_385 = {0};
static HexaIC __hexa_codegen_c2_ic_386 = {0};
static HexaIC __hexa_codegen_c2_ic_387 = {0};
static HexaIC __hexa_codegen_c2_ic_388 = {0};
static HexaIC __hexa_codegen_c2_ic_389 = {0};
static HexaIC __hexa_codegen_c2_ic_390 = {0};
static HexaIC __hexa_codegen_c2_ic_391 = {0};
static HexaIC __hexa_codegen_c2_ic_392 = {0};
static HexaIC __hexa_codegen_c2_ic_393 = {0};
static HexaIC __hexa_codegen_c2_ic_394 = {0};
static HexaIC __hexa_codegen_c2_ic_395 = {0};
static HexaIC __hexa_codegen_c2_ic_396 = {0};
static HexaIC __hexa_codegen_c2_ic_397 = {0};
static HexaIC __hexa_codegen_c2_ic_398 = {0};
static HexaIC __hexa_codegen_c2_ic_399 = {0};
static HexaIC __hexa_codegen_c2_ic_400 = {0};
static HexaIC __hexa_codegen_c2_ic_401 = {0};
static HexaIC __hexa_codegen_c2_ic_402 = {0};
static HexaIC __hexa_codegen_c2_ic_403 = {0};
static HexaIC __hexa_codegen_c2_ic_404 = {0};
static HexaIC __hexa_codegen_c2_ic_405 = {0};
static HexaIC __hexa_codegen_c2_ic_406 = {0};
static HexaIC __hexa_codegen_c2_ic_407 = {0};
static HexaIC __hexa_codegen_c2_ic_408 = {0};
static HexaIC __hexa_codegen_c2_ic_409 = {0};
static HexaIC __hexa_codegen_c2_ic_410 = {0};
static HexaIC __hexa_codegen_c2_ic_411 = {0};
static HexaIC __hexa_codegen_c2_ic_412 = {0};
static HexaIC __hexa_codegen_c2_ic_413 = {0};
static HexaIC __hexa_codegen_c2_ic_414 = {0};
static HexaIC __hexa_codegen_c2_ic_415 = {0};
static HexaIC __hexa_codegen_c2_ic_416 = {0};
static HexaIC __hexa_codegen_c2_ic_417 = {0};
static HexaIC __hexa_codegen_c2_ic_418 = {0};
static HexaIC __hexa_codegen_c2_ic_419 = {0};
static HexaIC __hexa_codegen_c2_ic_420 = {0};
static HexaIC __hexa_codegen_c2_ic_421 = {0};
static HexaIC __hexa_codegen_c2_ic_422 = {0};
static HexaIC __hexa_codegen_c2_ic_423 = {0};
static HexaIC __hexa_codegen_c2_ic_424 = {0};
static HexaIC __hexa_codegen_c2_ic_425 = {0};
static HexaIC __hexa_codegen_c2_ic_426 = {0};
static HexaIC __hexa_codegen_c2_ic_427 = {0};
static HexaIC __hexa_codegen_c2_ic_428 = {0};
static HexaIC __hexa_codegen_c2_ic_429 = {0};
static HexaIC __hexa_codegen_c2_ic_430 = {0};
static HexaIC __hexa_codegen_c2_ic_431 = {0};
static HexaIC __hexa_codegen_c2_ic_432 = {0};
static HexaIC __hexa_codegen_c2_ic_433 = {0};
static HexaIC __hexa_codegen_c2_ic_434 = {0};
static HexaIC __hexa_codegen_c2_ic_435 = {0};
static HexaIC __hexa_codegen_c2_ic_436 = {0};
static HexaIC __hexa_codegen_c2_ic_437 = {0};
static HexaIC __hexa_codegen_c2_ic_438 = {0};
static HexaIC __hexa_codegen_c2_ic_439 = {0};
static HexaIC __hexa_codegen_c2_ic_440 = {0};
static HexaIC __hexa_codegen_c2_ic_441 = {0};
static HexaIC __hexa_codegen_c2_ic_442 = {0};
static HexaIC __hexa_codegen_c2_ic_443 = {0};
static HexaIC __hexa_codegen_c2_ic_444 = {0};
static HexaIC __hexa_codegen_c2_ic_445 = {0};
static HexaIC __hexa_codegen_c2_ic_446 = {0};
static HexaIC __hexa_codegen_c2_ic_447 = {0};
static HexaIC __hexa_codegen_c2_ic_448 = {0};
static HexaIC __hexa_codegen_c2_ic_449 = {0};
static HexaIC __hexa_codegen_c2_ic_450 = {0};
static HexaIC __hexa_codegen_c2_ic_451 = {0};
static HexaIC __hexa_codegen_c2_ic_452 = {0};
static HexaIC __hexa_codegen_c2_ic_453 = {0};
static HexaIC __hexa_codegen_c2_ic_454 = {0};
static HexaIC __hexa_codegen_c2_ic_455 = {0};
static HexaIC __hexa_codegen_c2_ic_456 = {0};
static HexaIC __hexa_codegen_c2_ic_457 = {0};
static HexaIC __hexa_codegen_c2_ic_458 = {0};
static HexaIC __hexa_codegen_c2_ic_459 = {0};
static HexaIC __hexa_codegen_c2_ic_460 = {0};
static HexaIC __hexa_codegen_c2_ic_461 = {0};
static HexaIC __hexa_codegen_c2_ic_462 = {0};
static HexaIC __hexa_codegen_c2_ic_463 = {0};
static HexaIC __hexa_codegen_c2_ic_464 = {0};
static HexaIC __hexa_codegen_c2_ic_465 = {0};
static HexaIC __hexa_codegen_c2_ic_466 = {0};
static HexaIC __hexa_codegen_c2_ic_467 = {0};
static HexaIC __hexa_codegen_c2_ic_468 = {0};
static HexaIC __hexa_codegen_c2_ic_469 = {0};
static HexaIC __hexa_codegen_c2_ic_470 = {0};
static HexaIC __hexa_codegen_c2_ic_471 = {0};
static HexaIC __hexa_codegen_c2_ic_472 = {0};
static HexaIC __hexa_codegen_c2_ic_473 = {0};
static HexaIC __hexa_codegen_c2_ic_474 = {0};
static HexaIC __hexa_codegen_c2_ic_475 = {0};
static HexaIC __hexa_codegen_c2_ic_476 = {0};
static HexaIC __hexa_codegen_c2_ic_477 = {0};
static HexaIC __hexa_codegen_c2_ic_478 = {0};
static HexaIC __hexa_codegen_c2_ic_479 = {0};
static HexaIC __hexa_codegen_c2_ic_480 = {0};
static HexaIC __hexa_codegen_c2_ic_481 = {0};
static HexaIC __hexa_codegen_c2_ic_482 = {0};
static HexaIC __hexa_codegen_c2_ic_483 = {0};
static HexaIC __hexa_codegen_c2_ic_484 = {0};
static HexaIC __hexa_codegen_c2_ic_485 = {0};
static HexaIC __hexa_codegen_c2_ic_486 = {0};
static HexaIC __hexa_codegen_c2_ic_487 = {0};
static HexaIC __hexa_codegen_c2_ic_488 = {0};
static HexaIC __hexa_codegen_c2_ic_489 = {0};
static HexaIC __hexa_codegen_c2_ic_490 = {0};
static HexaIC __hexa_codegen_c2_ic_491 = {0};
static HexaIC __hexa_codegen_c2_ic_492 = {0};
static HexaIC __hexa_codegen_c2_ic_493 = {0};
static HexaIC __hexa_codegen_c2_ic_494 = {0};
static HexaIC __hexa_codegen_c2_ic_495 = {0};
static HexaIC __hexa_codegen_c2_ic_496 = {0};
static HexaIC __hexa_codegen_c2_ic_497 = {0};
static HexaIC __hexa_codegen_c2_ic_498 = {0};
static HexaIC __hexa_codegen_c2_ic_499 = {0};
static HexaIC __hexa_codegen_c2_ic_500 = {0};
static HexaIC __hexa_codegen_c2_ic_501 = {0};
static HexaIC __hexa_codegen_c2_ic_502 = {0};
static HexaIC __hexa_codegen_c2_ic_503 = {0};
static HexaIC __hexa_codegen_c2_ic_504 = {0};
static HexaIC __hexa_codegen_c2_ic_505 = {0};
static HexaIC __hexa_codegen_c2_ic_506 = {0};
static HexaIC __hexa_codegen_c2_ic_507 = {0};
static HexaIC __hexa_codegen_c2_ic_508 = {0};
static HexaIC __hexa_codegen_c2_ic_509 = {0};
static HexaIC __hexa_codegen_c2_ic_510 = {0};
static HexaIC __hexa_codegen_c2_ic_511 = {0};
static HexaIC __hexa_codegen_c2_ic_512 = {0};
static HexaIC __hexa_codegen_c2_ic_513 = {0};
static HexaIC __hexa_codegen_c2_ic_514 = {0};
static HexaIC __hexa_codegen_c2_ic_515 = {0};
static HexaIC __hexa_codegen_c2_ic_516 = {0};
static HexaIC __hexa_codegen_c2_ic_517 = {0};
static HexaIC __hexa_codegen_c2_ic_518 = {0};
static HexaIC __hexa_codegen_c2_ic_519 = {0};
static HexaIC __hexa_codegen_c2_ic_520 = {0};
static HexaIC __hexa_codegen_c2_ic_521 = {0};
static HexaIC __hexa_codegen_c2_ic_522 = {0};
static HexaIC __hexa_codegen_c2_ic_523 = {0};
static HexaIC __hexa_codegen_c2_ic_524 = {0};
static HexaIC __hexa_codegen_c2_ic_525 = {0};
static HexaIC __hexa_codegen_c2_ic_526 = {0};
static HexaIC __hexa_codegen_c2_ic_527 = {0};
static HexaIC __hexa_codegen_c2_ic_528 = {0};
static HexaIC __hexa_codegen_c2_ic_529 = {0};
static HexaIC __hexa_codegen_c2_ic_530 = {0};
static HexaIC __hexa_codegen_c2_ic_531 = {0};
static HexaIC __hexa_codegen_c2_ic_532 = {0};
static HexaIC __hexa_codegen_c2_ic_533 = {0};
static HexaIC __hexa_codegen_c2_ic_534 = {0};
static HexaIC __hexa_codegen_c2_ic_535 = {0};
static HexaIC __hexa_codegen_c2_ic_536 = {0};
static HexaIC __hexa_codegen_c2_ic_537 = {0};
static HexaIC __hexa_codegen_c2_ic_538 = {0};
static HexaIC __hexa_codegen_c2_ic_539 = {0};
static HexaIC __hexa_codegen_c2_ic_540 = {0};
static HexaIC __hexa_codegen_c2_ic_541 = {0};
static HexaIC __hexa_codegen_c2_ic_542 = {0};
static HexaIC __hexa_codegen_c2_ic_543 = {0};
static HexaIC __hexa_codegen_c2_ic_544 = {0};
static HexaIC __hexa_codegen_c2_ic_545 = {0};
static HexaIC __hexa_codegen_c2_ic_546 = {0};
static HexaIC __hexa_codegen_c2_ic_547 = {0};
static HexaIC __hexa_codegen_c2_ic_548 = {0};
static HexaIC __hexa_codegen_c2_ic_549 = {0};
static HexaIC __hexa_codegen_c2_ic_550 = {0};
static HexaIC __hexa_codegen_c2_ic_551 = {0};
static HexaIC __hexa_codegen_c2_ic_552 = {0};
static HexaIC __hexa_codegen_c2_ic_553 = {0};
static HexaIC __hexa_codegen_c2_ic_554 = {0};
static HexaIC __hexa_codegen_c2_ic_555 = {0};
static HexaIC __hexa_codegen_c2_ic_556 = {0};
static HexaIC __hexa_codegen_c2_ic_557 = {0};
static HexaIC __hexa_codegen_c2_ic_558 = {0};
static HexaIC __hexa_codegen_c2_ic_559 = {0};
static HexaIC __hexa_codegen_c2_ic_560 = {0};
static HexaIC __hexa_codegen_c2_ic_561 = {0};
static HexaIC __hexa_codegen_c2_ic_562 = {0};
static HexaIC __hexa_codegen_c2_ic_563 = {0};
static HexaIC __hexa_codegen_c2_ic_564 = {0};
static HexaIC __hexa_codegen_c2_ic_565 = {0};
static HexaIC __hexa_codegen_c2_ic_566 = {0};
static HexaIC __hexa_codegen_c2_ic_567 = {0};
static HexaIC __hexa_codegen_c2_ic_568 = {0};
static HexaIC __hexa_codegen_c2_ic_569 = {0};
static HexaIC __hexa_codegen_c2_ic_570 = {0};
static HexaIC __hexa_codegen_c2_ic_571 = {0};
static HexaIC __hexa_codegen_c2_ic_572 = {0};
static HexaIC __hexa_codegen_c2_ic_573 = {0};
static HexaIC __hexa_codegen_c2_ic_574 = {0};
static HexaIC __hexa_codegen_c2_ic_575 = {0};
static HexaIC __hexa_codegen_c2_ic_576 = {0};
static HexaIC __hexa_codegen_c2_ic_577 = {0};
static HexaIC __hexa_codegen_c2_ic_578 = {0};
static HexaIC __hexa_codegen_c2_ic_579 = {0};
static HexaIC __hexa_codegen_c2_ic_580 = {0};
static HexaIC __hexa_codegen_c2_ic_581 = {0};
static HexaIC __hexa_codegen_c2_ic_582 = {0};
static HexaIC __hexa_codegen_c2_ic_583 = {0};
static HexaIC __hexa_codegen_c2_ic_584 = {0};
static HexaIC __hexa_codegen_c2_ic_585 = {0};
static HexaIC __hexa_codegen_c2_ic_586 = {0};
static HexaIC __hexa_codegen_c2_ic_587 = {0};
static HexaIC __hexa_codegen_c2_ic_588 = {0};
static HexaIC __hexa_codegen_c2_ic_589 = {0};
static HexaIC __hexa_codegen_c2_ic_590 = {0};
static HexaIC __hexa_codegen_c2_ic_591 = {0};
static HexaIC __hexa_codegen_c2_ic_592 = {0};
static HexaIC __hexa_codegen_c2_ic_593 = {0};
static HexaIC __hexa_codegen_c2_ic_594 = {0};
static HexaIC __hexa_codegen_c2_ic_595 = {0};
static HexaIC __hexa_codegen_c2_ic_596 = {0};
static HexaIC __hexa_codegen_c2_ic_597 = {0};
static HexaIC __hexa_codegen_c2_ic_598 = {0};
static HexaIC __hexa_codegen_c2_ic_599 = {0};
static HexaIC __hexa_codegen_c2_ic_600 = {0};
static HexaIC __hexa_codegen_c2_ic_601 = {0};
static HexaIC __hexa_codegen_c2_ic_602 = {0};
static HexaIC __hexa_codegen_c2_ic_603 = {0};
static HexaIC __hexa_codegen_c2_ic_604 = {0};
static HexaIC __hexa_codegen_c2_ic_605 = {0};
static HexaIC __hexa_codegen_c2_ic_606 = {0};
static HexaIC __hexa_codegen_c2_ic_607 = {0};
static HexaIC __hexa_codegen_c2_ic_608 = {0};
static HexaIC __hexa_codegen_c2_ic_609 = {0};
static HexaIC __hexa_codegen_c2_ic_610 = {0};
static HexaIC __hexa_codegen_c2_ic_611 = {0};
static HexaIC __hexa_codegen_c2_ic_612 = {0};
static HexaIC __hexa_codegen_c2_ic_613 = {0};
static HexaIC __hexa_codegen_c2_ic_614 = {0};
static HexaIC __hexa_codegen_c2_ic_615 = {0};
static HexaIC __hexa_codegen_c2_ic_616 = {0};
static HexaIC __hexa_codegen_c2_ic_617 = {0};
static HexaIC __hexa_codegen_c2_ic_618 = {0};
static HexaIC __hexa_codegen_c2_ic_619 = {0};
static HexaIC __hexa_codegen_c2_ic_620 = {0};
static HexaIC __hexa_codegen_c2_ic_621 = {0};
static HexaIC __hexa_codegen_c2_ic_622 = {0};
static HexaIC __hexa_codegen_c2_ic_623 = {0};
static HexaIC __hexa_codegen_c2_ic_624 = {0};
static HexaIC __hexa_codegen_c2_ic_625 = {0};
static HexaIC __hexa_codegen_c2_ic_626 = {0};
static HexaIC __hexa_codegen_c2_ic_627 = {0};
static HexaIC __hexa_codegen_c2_ic_628 = {0};
static HexaIC __hexa_codegen_c2_ic_629 = {0};
static HexaIC __hexa_codegen_c2_ic_630 = {0};
static HexaIC __hexa_codegen_c2_ic_631 = {0};
static HexaIC __hexa_codegen_c2_ic_632 = {0};

HexaVal _hexa_name_is_reserved(HexaVal s) {
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_INT")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_FLOAT")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_BOOL")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_STR")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_VOID")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_ARRAY")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_MAP")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_FN")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_CHAR")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("TAG_CLOSURE")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(s, hexa_str("main")))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal _hexa_mangle_ident(HexaVal name) {
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(name), hexa_str("string")))))) {
        return name;
    }
    if (hexa_truthy(_hexa_name_is_reserved(name))) {
        return hexa_add(hexa_str("u_"), name);
    }
    return name;
    return hexa_void();
}


HexaVal codegen_c2(HexaVal ast) {
    HexaVal parts = hexa_array_new();
    parts = hexa_array_push(parts, hexa_str("// Generated by HEXA self-host compiler\n"));
    parts = hexa_array_push(parts, hexa_str("#include \"runtime.c\"\n\n"));
    _known_fn_globals = hexa_array_new();
    _known_nonlocal_names = hexa_array_new();
    _lambda_counter = hexa_int(0);
    _lambda_def_parts = hexa_array_new();
    _ic_counter = hexa_int(0);
    _ic_def_parts = hexa_array_new();
    _comptime_const_names = hexa_array_new();
    _comptime_const_nodes = hexa_array_new();
    HexaVal _gi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(_gi); HexaVal __r=(hexa_int(hexa_len(ast))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal _gk = hexa_map_get_ic(hexa_index_get(ast, _gi), "kind", &__hexa_codegen_c2_ic_0);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(_gk, hexa_str("FnDecl"))) || hexa_truthy(hexa_eq(_gk, hexa_str("ExternFnDecl"))))) || hexa_truthy(hexa_eq(_gk, hexa_str("PureFnDecl"))))) || hexa_truthy(hexa_eq(_gk, hexa_str("OptimizeFnStmt")))))) {
            _known_fn_globals = hexa_array_push(_known_fn_globals, hexa_map_get_ic(hexa_index_get(ast, _gi), "name", &__hexa_codegen_c2_ic_1));
            _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, _gi), "name", &__hexa_codegen_c2_ic_2));
        } else {
            if (hexa_truthy(hexa_eq(_gk, hexa_str("StructDecl")))) {
                _known_fn_globals = hexa_array_push(_known_fn_globals, hexa_map_get_ic(hexa_index_get(ast, _gi), "name", &__hexa_codegen_c2_ic_3));
                _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, _gi), "name", &__hexa_codegen_c2_ic_4));
            } else {
                if (hexa_truthy(hexa_eq(_gk, hexa_str("EnumDecl")))) {
                    _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, _gi), "name", &__hexa_codegen_c2_ic_5));
                } else {
                    if (hexa_truthy(hexa_eq(_gk, hexa_str("ComptimeConst")))) {
                        _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, _gi), "name", &__hexa_codegen_c2_ic_6));
                    } else {
                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(_gk, hexa_str("LetMutStmt"))) || hexa_truthy(hexa_eq(_gk, hexa_str("LetStmt")))))) {
                            _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, _gi), "name", &__hexa_codegen_c2_ic_7));
                        }
                    }
                }
            }
        }
        _gi = hexa_add(_gi, hexa_int(1));
    }
    HexaVal fwd_parts = hexa_array_new();
    HexaVal global_parts = hexa_array_new();
    HexaVal fn_parts = hexa_array_new();
    HexaVal main_parts = hexa_array_new();
    HexaVal extern_fns = hexa_array_new();
    HexaVal has_user_main = hexa_bool(0);
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(ast))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal k = hexa_map_get_ic(hexa_index_get(ast, i), "kind", &__hexa_codegen_c2_ic_8);
        if (hexa_truthy(hexa_eq(k, hexa_str("FnDecl")))) {
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_9), hexa_str("main")))) {
                has_user_main = hexa_bool(1);
            }
            fwd_parts = hexa_array_push(fwd_parts, hexa_add(gen2_fn_forward(hexa_index_get(ast, i)), hexa_str("\n")));
            fn_parts = hexa_array_push(fn_parts, hexa_add(gen2_fn_decl(hexa_index_get(ast, i)), hexa_str("\n\n")));
        } else {
            if (hexa_truthy(hexa_eq(k, hexa_str("ExternFnDecl")))) {
                extern_fns = hexa_array_push(extern_fns, hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_10));
                HexaVal ew = gen2_extern_wrapper(hexa_index_get(ast, i));
                global_parts = hexa_array_push(global_parts, hexa_map_get_ic(ew, "global", &__hexa_codegen_c2_ic_11));
                fwd_parts = hexa_array_push(fwd_parts, hexa_add(hexa_map_get_ic(ew, "forward", &__hexa_codegen_c2_ic_12), hexa_str("\n")));
                fn_parts = hexa_array_push(fn_parts, hexa_add(hexa_map_get_ic(ew, "fn_code", &__hexa_codegen_c2_ic_13), hexa_str("\n\n")));
                main_parts = hexa_array_push(main_parts, hexa_map_get_ic(ew, "init", &__hexa_codegen_c2_ic_14));
            } else {
                if (hexa_truthy(hexa_eq(k, hexa_str("StructDecl")))) {
                    fwd_parts = hexa_array_push(fwd_parts, hexa_add(gen2_struct_forward(hexa_index_get(ast, i)), hexa_str("\n")));
                    fn_parts = hexa_array_push(fn_parts, hexa_add(gen2_struct_decl(hexa_index_get(ast, i)), hexa_str("\n\n")));
                } else {
                    if (hexa_truthy(hexa_eq(k, hexa_str("EnumDecl")))) {
                        fn_parts = hexa_array_push(fn_parts, hexa_add(gen2_enum_decl(hexa_index_get(ast, i)), hexa_str("\n")));
                    } else {
                        if (hexa_truthy(hexa_eq(k, hexa_str("ImplBlock")))) {
                            HexaVal ib = gen2_impl_block(hexa_index_get(ast, i));
                            fwd_parts = hexa_array_push(fwd_parts, hexa_map_get_ic(ib, "forward", &__hexa_codegen_c2_ic_15));
                            fn_parts = hexa_array_push(fn_parts, hexa_map_get_ic(ib, "fn_code", &__hexa_codegen_c2_ic_16));
                        } else {
                            if (hexa_truthy(hexa_eq(k, hexa_str("PureFnDecl")))) {
                                fwd_parts = hexa_array_push(fwd_parts, hexa_add(gen2_fn_forward(hexa_index_get(ast, i)), hexa_str("\n")));
                                fn_parts = hexa_array_push(fn_parts, hexa_add(gen2_fn_decl(hexa_index_get(ast, i)), hexa_str("\n\n")));
                            } else {
                                if (hexa_truthy(hexa_eq(k, hexa_str("ComptimeConst")))) {
                                    HexaVal _cc_folded = comptime_eval(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_17));
                                    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(_cc_folded), hexa_str("string")))))) {
                                        _register_comptime_const(hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_18), _cc_folded);
                                    } else {
                                        global_parts = hexa_array_push(global_parts, hexa_add(hexa_add(hexa_str("HexaVal "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_19)), hexa_str(";\n")));
                                        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_20)), hexa_str("string")))))) {
                                            main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_21)), hexa_str(" = ")), gen2_expr(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_22))), hexa_str(";\n")));
                                        } else {
                                            main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_str("    "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_23)), hexa_str(" = hexa_void();\n")));
                                        }
                                    }
                                } else {
                                    if (hexa_truthy(hexa_eq(k, hexa_str("OptimizeFnStmt")))) {
                                    } else {
                                        if (hexa_truthy(hexa_eq(k, hexa_str("TraitDecl")))) {
                                        } else {
                                            if (hexa_truthy(hexa_eq(k, hexa_str("InvariantDecl")))) {
                                            } else {
                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("ImportStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("UseStmt")))))) {
                                                    (hexa_eprint_val(hexa_add(hexa_str("[codegen_c2] WARNING: import/use not fully resolved: "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_24))), fprintf(stderr, "\n"), hexa_void());
                                                    main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_str("    /* import: "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_25)), hexa_str(" */\n")));
                                                } else {
                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("LetMutStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("LetStmt")))))) {
                                                        HexaVal _user_name = _hexa_mangle_ident(hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_26));
                                                        HexaVal _tls_val = hexa_map_get_ic(hexa_index_get(ast, i), "value", &__hexa_codegen_c2_ic_27);
                                                        HexaVal _is_tls = hexa_bool(0);
                                                        if (hexa_truthy(hexa_eq(hexa_type_of(_tls_val), hexa_str("string")))) {
                                                            if (hexa_truthy(hexa_eq(_tls_val, hexa_str("thread_local")))) {
                                                                _is_tls = hexa_bool(1);
                                                            }
                                                        }
                                                        if (hexa_truthy(_is_tls)) {
                                                            global_parts = hexa_array_push(global_parts, hexa_add(hexa_add(hexa_str("_Thread_local HexaVal "), _user_name), hexa_str(";\n")));
                                                        } else {
                                                            global_parts = hexa_array_push(global_parts, hexa_add(hexa_add(hexa_str("HexaVal "), _user_name), hexa_str(";\n")));
                                                        }
                                                        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_28)), hexa_str("string")))))) {
                                                            main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    "), _user_name), hexa_str(" = ")), gen2_expr(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_29))), hexa_str(";\n")));
                                                        } else {
                                                            main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_str("    "), _user_name), hexa_str(" = hexa_void();\n")));
                                                        }
                                                    } else {
                                                        main_parts = hexa_array_push(main_parts, gen2_stmt(hexa_index_get(ast, i), hexa_int(1)));
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        i = hexa_add(i, hexa_int(1));
    }
    parts = hexa_array_push(parts, hexa_str_join(fwd_parts, hexa_str("")));
    parts = hexa_array_push(parts, hexa_str("\n"));
    parts = hexa_array_push(parts, hexa_str_join(global_parts, hexa_str("")));
    parts = hexa_array_push(parts, hexa_str("\n"));
    parts = hexa_array_push(parts, hexa_str_join(_ic_def_parts, hexa_str("")));
    parts = hexa_array_push(parts, hexa_str("\n"));
    parts = hexa_array_push(parts, hexa_str_join(_lambda_def_parts, hexa_str("")));
    parts = hexa_array_push(parts, hexa_str_join(fn_parts, hexa_str("")));
    parts = hexa_array_push(parts, hexa_str("int main(int argc, char** argv) {\n"));
    parts = hexa_array_push(parts, hexa_str("    hexa_set_args(argc, argv);\n"));
    parts = hexa_array_push(parts, hexa_str_join(main_parts, hexa_str("")));
    if (hexa_truthy(has_user_main)) {
        parts = hexa_array_push(parts, hexa_str("    u_main();\n"));
    }
    parts = hexa_array_push(parts, hexa_str("    return 0;\n}\n"));
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_has_attr(HexaVal node, HexaVal target) {
    HexaVal v = hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_30);
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(v), hexa_str("string")))))) {
        return hexa_bool(0);
    }
    if (hexa_truthy(hexa_eq(v, hexa_str("")))) {
        return hexa_bool(0);
    }
    HexaVal chars = hexa_str_chars(v);
    HexaVal total = hexa_int(hexa_len(chars));
    HexaVal i2 = hexa_int(0);
    HexaVal cur = hexa_str("");
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i2); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal c = hexa_to_string(hexa_index_get(chars, i2));
        if (hexa_truthy(hexa_eq(c, hexa_str(",")))) {
            if (hexa_truthy(hexa_eq(cur, target))) {
                return hexa_bool(1);
            }
            cur = hexa_str("");
        } else {
            cur = hexa_add(cur, c);
        }
        i2 = hexa_add(i2, hexa_int(1));
    }
    if (hexa_truthy(hexa_eq(cur, target))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal gen2_has_inline_always(HexaVal node) {
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_31)), hexa_str("string")))))) {
        return hexa_bool(0);
    }
    if (hexa_truthy(hexa_eq(hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_32), hexa_str("")))) {
        return hexa_bool(0);
    }
    HexaVal attrs = hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_33);
    HexaVal chars = hexa_str_chars(attrs);
    HexaVal total = hexa_int(hexa_len(chars));
    HexaVal i = hexa_int(0);
    HexaVal cur = hexa_str("");
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(total); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal c = hexa_to_string(hexa_index_get(chars, i));
        if (hexa_truthy(hexa_eq(c, hexa_str(",")))) {
            if (hexa_truthy(hexa_eq(cur, hexa_str("inline_always")))) {
                return hexa_bool(1);
            }
            cur = hexa_str("");
        } else {
            cur = hexa_add(cur, c);
        }
        i = hexa_add(i, hexa_int(1));
    }
    if (hexa_truthy(hexa_eq(cur, hexa_str("inline_always")))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal gen2_fn_forward(HexaVal node) {
    HexaVal has_restrict = gen2_has_attr(node, hexa_str("restrict"));
    HexaVal params = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_34)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(has_restrict)) {
            params = hexa_array_push(params, hexa_add(hexa_str("HexaVal __restrict "), hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_35), i), "name", &__hexa_codegen_c2_ic_36)));
        } else {
            params = hexa_array_push(params, hexa_add(hexa_str("HexaVal "), hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_37), i), "name", &__hexa_codegen_c2_ic_38)));
        }
        i = hexa_add(i, hexa_int(1));
    }
    HexaVal p = hexa_str_join(params, hexa_str(", "));
    if (hexa_truthy(hexa_eq(p, hexa_str("")))) {
        p = hexa_str("void");
    }
    HexaVal prefix = hexa_str("");
    if (hexa_truthy(gen2_has_inline_always(node))) {
        prefix = hexa_str("static inline ");
    }
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(prefix, hexa_str("HexaVal ")), _hexa_mangle_ident(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_39))), hexa_str("(")), p), hexa_str(");"));
    return hexa_void();
}


HexaVal gen2_has_specialize(HexaVal node) {
    HexaVal attrs = hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_40);
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(attrs), hexa_str("string")))))) {
        return hexa_bool(0);
    }
    if (hexa_truthy(hexa_eq(attrs, hexa_str("specialize")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_bool(hexa_str_contains(attrs, hexa_str("specialize"))))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal gen2_specialize_guard(HexaVal node) {
    if (hexa_truthy(hexa_eq(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_41))), hexa_int(0)))) {
        return hexa_str("");
    }
    HexaVal p0 = hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_42), hexa_int(0)), "name", &__hexa_codegen_c2_ic_43);
    HexaVal out = hexa_str("");
    out = hexa_add(out, hexa_str("    /* @specialize: inline cache type guard */\n"));
    out = hexa_add(hexa_add(hexa_add(out, hexa_str("    if (")), p0), hexa_str(".tag == TAG_INT) {\n"));
    out = hexa_add(out, hexa_str("        /* monomorphic int fast-path: skip tag checks */\n"));
    out = hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(out, hexa_str("        int64_t __spec_")), p0), hexa_str(" = ")), p0), hexa_str(".i;\n"));
    out = hexa_add(hexa_add(hexa_add(out, hexa_str("        (void)__spec_")), p0), hexa_str("; /* hint for optimizer */\n"));
    out = hexa_add(out, hexa_str("    }\n"));
    return out;
    return hexa_void();
}


HexaVal gen2_fn_decl(HexaVal node) {
    HexaVal has_restrict = gen2_has_attr(node, hexa_str("restrict"));
    HexaVal has_flatten = gen2_has_attr(node, hexa_str("flatten"));
    HexaVal params = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_44)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(has_restrict)) {
            params = hexa_array_push(params, hexa_add(hexa_str("HexaVal __restrict "), hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_45), i), "name", &__hexa_codegen_c2_ic_46)));
        } else {
            params = hexa_array_push(params, hexa_add(hexa_str("HexaVal "), hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_47), i), "name", &__hexa_codegen_c2_ic_48)));
        }
        i = hexa_add(i, hexa_int(1));
    }
    HexaVal p = hexa_str_join(params, hexa_str(", "));
    if (hexa_truthy(hexa_eq(p, hexa_str("")))) {
        p = hexa_str("void");
    }
    HexaVal has_stack_alloc = hexa_bool(0);
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_49)), hexa_str("string"))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_50), hexa_str("")))))))) {
        HexaVal _sa_attrs = hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_51);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(_sa_attrs, hexa_str("stack_alloc"))) || hexa_truthy(hexa_eq(_sa_attrs, hexa_str("optimize,stack_alloc"))))) || hexa_truthy(hexa_eq(_sa_attrs, hexa_str("stack_alloc,optimize")))))) {
            has_stack_alloc = hexa_bool(1);
        }
        HexaVal _sa_chars = hexa_str_chars(_sa_attrs);
        HexaVal _sa_len = hexa_int(hexa_len(_sa_chars));
        HexaVal _sa_cur = hexa_str("");
        HexaVal _sa_ci = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(_sa_ci); HexaVal __r=(_sa_len); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal _sa_ch = hexa_to_string(hexa_index_get(_sa_chars, _sa_ci));
            if (hexa_truthy(hexa_eq(_sa_ch, hexa_str(",")))) {
                if (hexa_truthy(hexa_eq(_sa_cur, hexa_str("stack_alloc")))) {
                    has_stack_alloc = hexa_bool(1);
                }
                _sa_cur = hexa_str("");
            } else {
                _sa_cur = hexa_add(_sa_cur, _sa_ch);
            }
            _sa_ci = hexa_add(_sa_ci, hexa_int(1));
        }
        if (hexa_truthy(hexa_eq(_sa_cur, hexa_str("stack_alloc")))) {
            has_stack_alloc = hexa_bool(1);
        }
    }
    _gen2_declared_names = hexa_array_new();
    HexaVal _pi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(_pi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_52)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        _gen2_declared_names = hexa_array_push(_gen2_declared_names, hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_53), _pi), "name", &__hexa_codegen_c2_ic_54));
        _pi = hexa_add(_pi, hexa_int(1));
    }
    HexaVal all_names = _gen2_collect_lets(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_55), hexa_array_new());
    HexaVal _hoisted = hexa_array_new();
    HexaVal hoists = hexa_array_new();
    HexaVal ii = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ii); HexaVal __r=(hexa_int(hexa_len(all_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal nm = hexa_index_get(all_names, ii);
        HexaVal already = _gen2_has_decl(nm);
        HexaVal jj = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(jj); HexaVal __r=(hexa_int(hexa_len(_hoisted))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            if (hexa_truthy(hexa_eq(hexa_index_get(_hoisted, jj), nm))) {
                already = hexa_bool(1);
            }
            jj = hexa_add(jj, hexa_int(1));
        }
        if (hexa_truthy(hexa_bool(!hexa_truthy(already)))) {
            HexaVal cnt = hexa_int(0);
            HexaVal kk = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(kk); HexaVal __r=(hexa_int(hexa_len(all_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                if (hexa_truthy(hexa_eq(hexa_index_get(all_names, kk), nm))) {
                    cnt = hexa_add(cnt, hexa_int(1));
                }
                kk = hexa_add(kk, hexa_int(1));
            }
            if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(cnt); HexaVal __r=(hexa_int(1)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                _hoisted = hexa_array_push(_hoisted, nm);
                _gen2_declared_names = hexa_array_push(_gen2_declared_names, nm);
                hoists = hexa_array_push(hoists, hexa_add(hexa_add(hexa_str("    HexaVal "), nm), hexa_str(" = hexa_void();\n")));
            }
        }
        ii = hexa_add(ii, hexa_int(1));
    }
    HexaVal chunks = hexa_array_new();
    if (hexa_truthy(has_flatten)) {
        chunks = hexa_array_push(chunks, hexa_str("/* @flatten: SROA — struct params decomposed to scalars */\n"));
    }
    HexaVal _fn_name = _hexa_mangle_ident(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_56));
    HexaVal prefix = hexa_str("");
    if (hexa_truthy(gen2_has_inline_always(node))) {
        prefix = hexa_str("static inline ");
    }
    chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(prefix, hexa_str("HexaVal ")), _fn_name), hexa_str("(")), p), hexa_str(") {\n")));
    if (hexa_truthy(gen2_has_specialize(node))) {
        chunks = hexa_array_push(chunks, gen2_specialize_guard(node));
    }
    HexaVal hj = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hj); HexaVal __r=(hexa_int(hexa_len(hoists))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        chunks = hexa_array_push(chunks, hexa_index_get(hoists, hj));
        hj = hexa_add(hj, hexa_int(1));
    }
    if (hexa_truthy(has_stack_alloc)) {
        chunks = hexa_array_push(chunks, hexa_str("    /* @stack_alloc: bounded arrays use alloca */\n"));
    }
    HexaVal _ret_type = hexa_map_get_ic(node, "ret_type", &__hexa_codegen_c2_ic_57);
    HexaVal _wants_tail_return = hexa_bool(1);
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(_ret_type), hexa_str("string")))))) {
        _wants_tail_return = hexa_bool(0);
    }
    if (hexa_truthy(hexa_eq(_ret_type, hexa_str("")))) {
        _wants_tail_return = hexa_bool(0);
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(_ret_type, hexa_str("Void"))) || hexa_truthy(hexa_eq(_ret_type, hexa_str("void"))))) || hexa_truthy(hexa_eq(_ret_type, hexa_str("()")))))) {
        _wants_tail_return = hexa_bool(0);
    }
    HexaVal body_len = hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_58)));
    HexaVal bi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(bi); HexaVal __r=(body_len); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal stmt = hexa_index_get(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_59), bi);
        HexaVal did_emit_return = hexa_bool(0);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(_wants_tail_return) && hexa_truthy(hexa_eq(bi, hexa_sub(body_len, hexa_int(1)))))) && hexa_truthy(hexa_bool(!hexa_truthy(has_stack_alloc)))))) {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(stmt), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(stmt, "kind", &__hexa_codegen_c2_ic_60), hexa_str("ExprStmt")))))) {
                if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(stmt, "left", &__hexa_codegen_c2_ic_61)), hexa_str("string")))))) {
                    HexaVal inner_kind = hexa_map_get_ic(hexa_map_get_ic(stmt, "left", &__hexa_codegen_c2_ic_62), "kind", &__hexa_codegen_c2_ic_63);
                    HexaVal _skip = hexa_bool(0);
                    if (hexa_truthy(hexa_eq(inner_kind, hexa_str("IfExpr")))) {
                        _skip = hexa_bool(1);
                    }
                    if (hexa_truthy(hexa_eq(inner_kind, hexa_str("MatchExpr")))) {
                        _skip = hexa_bool(1);
                    }
                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(inner_kind, hexa_str("Call"))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(hexa_map_get_ic(stmt, "left", &__hexa_codegen_c2_ic_64), "left", &__hexa_codegen_c2_ic_65)), hexa_str("string")))))))) {
                        if (hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_map_get_ic(hexa_map_get_ic(stmt, "left", &__hexa_codegen_c2_ic_66), "left", &__hexa_codegen_c2_ic_67), "kind", &__hexa_codegen_c2_ic_68), hexa_str("Ident")))) {
                            HexaVal _cname = hexa_map_get_ic(hexa_map_get_ic(hexa_map_get_ic(stmt, "left", &__hexa_codegen_c2_ic_69), "left", &__hexa_codegen_c2_ic_70), "name", &__hexa_codegen_c2_ic_71);
                            if (hexa_truthy(hexa_eq(_cname, hexa_str("println")))) {
                                _skip = hexa_bool(1);
                            }
                            if (hexa_truthy(hexa_eq(_cname, hexa_str("print")))) {
                                _skip = hexa_bool(1);
                            }
                            if (hexa_truthy(hexa_eq(_cname, hexa_str("eprintln")))) {
                                _skip = hexa_bool(1);
                            }
                            if (hexa_truthy(hexa_eq(_cname, hexa_str("exit")))) {
                                _skip = hexa_bool(1);
                            }
                        }
                    }
                    if (hexa_truthy(hexa_bool(!hexa_truthy(_skip)))) {
                        chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_str("    return "), gen2_expr(hexa_map_get_ic(stmt, "left", &__hexa_codegen_c2_ic_72))), hexa_str(";\n")));
                        did_emit_return = hexa_bool(1);
                    }
                }
            }
        }
        if (hexa_truthy(hexa_bool(!hexa_truthy(did_emit_return)))) {
            if (hexa_truthy(has_stack_alloc)) {
                chunks = hexa_array_push(chunks, gen2_stmt_stack_alloc(stmt, hexa_int(1)));
            } else {
                chunks = hexa_array_push(chunks, gen2_stmt(stmt, hexa_int(1)));
            }
        }
        bi = hexa_add(bi, hexa_int(1));
    }
    chunks = hexa_array_push(chunks, hexa_str("    return hexa_void();\n}\n"));
    return hexa_str_join(chunks, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_stmt_stack_alloc(HexaVal node, HexaVal depth) {
    HexaVal pad = gen2_indent(depth);
    HexaVal k = hexa_map_get_ic(node, "kind", &__hexa_codegen_c2_ic_73);
    if (hexa_truthy(hexa_eq(k, hexa_str("LetMutStmt")))) {
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_74)), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_75), "kind", &__hexa_codegen_c2_ic_76), hexa_str("ArrayLit")))))) {
            return hexa_add(hexa_add(hexa_add(pad, hexa_str("/* @stack_alloc */ HexaVal ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_77)), hexa_str(" = hexa_stack_array(1024);\n"));
        }
    }
    return gen2_stmt(node, depth);
    return hexa_void();
}


HexaVal gen2_extern_ret_kind(HexaVal ret_type) {
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Void"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("void"))))) || hexa_truthy(hexa_eq(ret_type, hexa_str("")))))) {
        return hexa_str("0");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Int"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("int")))))) {
        return hexa_str("1");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Float"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("float"))))) || hexa_truthy(hexa_eq(ret_type, hexa_str("f64"))))) || hexa_truthy(hexa_eq(ret_type, hexa_str("f32")))))) {
        return hexa_str("2");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Bool"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("bool")))))) {
        return hexa_str("3");
    }
    return hexa_str("4");
    return hexa_void();
}


HexaVal gen2_ffi_c_type(HexaVal typ) {
    if (hexa_truthy(hexa_eq(typ, hexa_str("f32")))) {
        return hexa_str("float");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(typ, hexa_str("Float"))) || hexa_truthy(hexa_eq(typ, hexa_str("float"))))) || hexa_truthy(hexa_eq(typ, hexa_str("f64")))))) {
        return hexa_str("double");
    }
    return hexa_str("int64_t");
    return hexa_void();
}


HexaVal gen2_ffi_c_ret_type(HexaVal ret_type) {
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Void"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("void"))))) || hexa_truthy(hexa_eq(ret_type, hexa_str("")))))) {
        return hexa_str("void");
    }
    if (hexa_truthy(hexa_eq(ret_type, hexa_str("f32")))) {
        return hexa_str("float");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Float"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("float"))))) || hexa_truthy(hexa_eq(ret_type, hexa_str("f64")))))) {
        return hexa_str("double");
    }
    return hexa_str("int64_t");
    return hexa_void();
}


HexaVal gen2_has_float_param(HexaVal params) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(params))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal t = hexa_map_get_ic(hexa_index_get(params, i), "value", &__hexa_codegen_c2_ic_78);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(t, hexa_str("Float"))) || hexa_truthy(hexa_eq(t, hexa_str("float"))))) || hexa_truthy(hexa_eq(t, hexa_str("f64"))))) || hexa_truthy(hexa_eq(t, hexa_str("f32")))))) {
            return hexa_int(1);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_int(0);
    return hexa_void();
}


HexaVal gen2_ffi_marshal_arg(HexaVal param_name, HexaVal param_type) {
    if (hexa_truthy(hexa_eq(param_type, hexa_str("f32")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("(float)("), param_name), hexa_str(".tag==TAG_FLOAT?")), param_name), hexa_str(".f:(double)")), param_name), hexa_str(".i)"));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(param_type, hexa_str("Float"))) || hexa_truthy(hexa_eq(param_type, hexa_str("float"))))) || hexa_truthy(hexa_eq(param_type, hexa_str("f64")))))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("("), param_name), hexa_str(".tag==TAG_FLOAT?")), param_name), hexa_str(".f:(double)")), param_name), hexa_str(".i)"));
    }
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("("), param_name), hexa_str(".tag==TAG_INT?")), param_name), hexa_str(".i:(int64_t)")), param_name), hexa_str(".f)"));
    return hexa_void();
}


HexaVal gen2_ffi_wrap_ret(HexaVal ret_type, HexaVal var_name) {
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Void"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("void"))))) || hexa_truthy(hexa_eq(ret_type, hexa_str("")))))) {
        return hexa_str("hexa_void()");
    }
    if (hexa_truthy(hexa_eq(ret_type, hexa_str("f32")))) {
        return hexa_add(hexa_add(hexa_str("hexa_float((double)"), var_name), hexa_str(")"));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Float"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("float"))))) || hexa_truthy(hexa_eq(ret_type, hexa_str("f64")))))) {
        return hexa_add(hexa_add(hexa_str("hexa_float("), var_name), hexa_str(")"));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Bool"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("bool")))))) {
        return hexa_add(hexa_add(hexa_str("hexa_bool("), var_name), hexa_str(" != 0)"));
    }
    return hexa_add(hexa_add(hexa_str("hexa_int("), var_name), hexa_str(")"));
    return hexa_void();
}


HexaVal gen2_static_c_type(HexaVal typ) {
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(typ, hexa_str("i64"))) || hexa_truthy(hexa_eq(typ, hexa_str("Int"))))) || hexa_truthy(hexa_eq(typ, hexa_str("int")))))) {
        return hexa_str("long long");
    }
    if (hexa_truthy(hexa_eq(typ, hexa_str("i32")))) {
        return hexa_str("int");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(typ, hexa_str("f64"))) || hexa_truthy(hexa_eq(typ, hexa_str("Float"))))) || hexa_truthy(hexa_eq(typ, hexa_str("float")))))) {
        return hexa_str("double");
    }
    if (hexa_truthy(hexa_eq(typ, hexa_str("f32")))) {
        return hexa_str("float");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(typ, hexa_str("str"))) || hexa_truthy(hexa_eq(typ, hexa_str("Str"))))) || hexa_truthy(hexa_eq(typ, hexa_str("String")))))) {
        return hexa_str("char*");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(typ, hexa_str("bool"))) || hexa_truthy(hexa_eq(typ, hexa_str("Bool")))))) {
        return hexa_str("int");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(typ, hexa_str("void"))) || hexa_truthy(hexa_eq(typ, hexa_str("Void"))))) || hexa_truthy(hexa_eq(typ, hexa_str("")))))) {
        return hexa_str("void");
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(typ, hexa_str("*Void"))) || hexa_truthy(hexa_eq(typ, hexa_str("Ptr")))))) {
        return hexa_str("void*");
    }
    return typ;
    return hexa_void();
}


HexaVal gen2_extern_static_decl(HexaVal node) {
    HexaVal name = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_79);
    HexaVal ret_type = hexa_map_get_ic(node, "ret_type", &__hexa_codegen_c2_ic_80);
    HexaVal c_name = hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_81);
    if (hexa_truthy(hexa_eq(c_name, hexa_str("")))) {
        c_name = name;
    }
    HexaVal c_ret = gen2_static_c_type(ret_type);
    HexaVal c_params = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_82)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal p = hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_83), i);
        HexaVal c_typ = gen2_static_c_type(hexa_map_get_ic(p, "value", &__hexa_codegen_c2_ic_84));
        if (hexa_truthy(hexa_eq(c_typ, hexa_str("void")))) {
            c_params = hexa_array_push(c_params, hexa_add(hexa_str("long long "), hexa_map_get_ic(p, "name", &__hexa_codegen_c2_ic_85)));
        } else {
            c_params = hexa_array_push(c_params, hexa_add(hexa_add(c_typ, hexa_str(" ")), hexa_map_get_ic(p, "name", &__hexa_codegen_c2_ic_86)));
        }
        i = hexa_add(i, hexa_int(1));
    }
    HexaVal params_str = hexa_str_join(c_params, hexa_str(", "));
    HexaVal sig = params_str;
    if (hexa_truthy(hexa_eq(sig, hexa_str("")))) {
        sig = hexa_str("void");
    }
    HexaVal parts = hexa_array_new();
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_87), hexa_str("")))))) {
        parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("// link: -l"), hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_88)), hexa_str("\n")));
    }
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("extern "), c_ret), hexa_str(" ")), c_name), hexa_str("(")), sig), hexa_str(");\n")));
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_extern_includes(HexaVal ast) {
    HexaVal needs_stdio = hexa_int(0);
    HexaVal needs_stdlib = hexa_int(0);
    HexaVal needs_string = hexa_int(0);
    HexaVal needs_math = hexa_int(0);
    HexaVal has_extern = hexa_int(0);
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(ast))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_index_get(ast, i), "kind", &__hexa_codegen_c2_ic_89), hexa_str("ExternFnDecl")))) {
            has_extern = hexa_int(1);
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_index_get(ast, i), "op", &__hexa_codegen_c2_ic_90), hexa_str("m"))) || hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_index_get(ast, i), "op", &__hexa_codegen_c2_ic_91), hexa_str("libm")))))) {
                needs_math = hexa_int(1);
            }
            HexaVal j = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(j); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(hexa_index_get(ast, i), "params", &__hexa_codegen_c2_ic_92)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                HexaVal t = hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(hexa_index_get(ast, i), "params", &__hexa_codegen_c2_ic_93), j), "value", &__hexa_codegen_c2_ic_94);
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(t, hexa_str("str"))) || hexa_truthy(hexa_eq(t, hexa_str("Str"))))) || hexa_truthy(hexa_eq(t, hexa_str("String")))))) {
                    needs_string = hexa_int(1);
                }
                j = hexa_add(j, hexa_int(1));
            }
            HexaVal rt = hexa_map_get_ic(hexa_index_get(ast, i), "ret_type", &__hexa_codegen_c2_ic_95);
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(rt, hexa_str("str"))) || hexa_truthy(hexa_eq(rt, hexa_str("Str"))))) || hexa_truthy(hexa_eq(rt, hexa_str("String")))))) {
                needs_string = hexa_int(1);
            }
        }
        i = hexa_add(i, hexa_int(1));
    }
    if (hexa_truthy(hexa_eq(has_extern, hexa_int(0)))) {
        return hexa_str("");
    }
    HexaVal includes = hexa_array_new();
    includes = hexa_array_push(includes, hexa_str("#include <stdint.h>\n"));
    if (hexa_truthy(hexa_eq(needs_math, hexa_int(1)))) {
        includes = hexa_array_push(includes, hexa_str("#include <math.h>\n"));
    }
    if (hexa_truthy(hexa_eq(needs_string, hexa_int(1)))) {
        includes = hexa_array_push(includes, hexa_str("#include <string.h>\n"));
    }
    return hexa_str_join(includes, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_static_ffi_block(HexaVal ast) {
    HexaVal includes = gen2_extern_includes(ast);
    HexaVal decls = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(ast))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_index_get(ast, i), "kind", &__hexa_codegen_c2_ic_96), hexa_str("ExternFnDecl")))) {
            decls = hexa_array_push(decls, gen2_extern_static_decl(hexa_index_get(ast, i)));
        }
        i = hexa_add(i, hexa_int(1));
    }
    if (hexa_truthy(hexa_eq(hexa_int(hexa_len(decls)), hexa_int(0)))) {
        return hexa_str("");
    }
    HexaVal parts = hexa_array_new();
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(includes, hexa_str("")))))) {
        parts = hexa_array_push(parts, includes);
    }
    parts = hexa_array_push(parts, hexa_str("\n// ── FFI declarations ──\n"));
    parts = hexa_array_push(parts, hexa_str_join(decls, hexa_str("")));
    parts = hexa_array_push(parts, hexa_str("\n"));
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_extern_wrapper(HexaVal node) {
    HexaVal name = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_97);
    HexaVal nargs = hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_98)));
    HexaVal ret_type = hexa_map_get_ic(node, "ret_type", &__hexa_codegen_c2_ic_99);
    HexaVal c_sym = hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_100);
    if (hexa_truthy(hexa_eq(c_sym, hexa_str("")))) {
        c_sym = name;
    }
    HexaVal global = hexa_add(hexa_add(hexa_str("static void* __ffi_sym_"), name), hexa_str(" = NULL;\n"));
    HexaVal fwd_params = hexa_array_new();
    HexaVal fi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(nargs); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        fwd_params = hexa_array_push(fwd_params, hexa_add(hexa_str("HexaVal "), hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_101), fi), "name", &__hexa_codegen_c2_ic_102)));
        fi = hexa_add(fi, hexa_int(1));
    }
    HexaVal fwd_p = hexa_str_join(fwd_params, hexa_str(", "));
    HexaVal sig_p = fwd_p;
    if (hexa_truthy(hexa_eq(sig_p, hexa_str("")))) {
        sig_p = hexa_str("void");
    }
    HexaVal forward = hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("static HexaVal "), name), hexa_str("(")), sig_p), hexa_str(");"));
    HexaVal has_float = gen2_has_float_param(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_103));
    HexaVal impl_parts = hexa_array_new();
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(has_float, hexa_int(1))) || hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(nargs); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))))) {
        HexaVal c_ret = gen2_ffi_c_ret_type(ret_type);
        HexaVal typedef_params = hexa_array_new();
        HexaVal ti = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ti); HexaVal __r=(nargs); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            typedef_params = hexa_array_push(typedef_params, gen2_ffi_c_type(hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_104), ti), "value", &__hexa_codegen_c2_ic_105)));
            ti = hexa_add(ti, hexa_int(1));
        }
        HexaVal td_p = hexa_str_join(typedef_params, hexa_str(", "));
        HexaVal td_sig = td_p;
        if (hexa_truthy(hexa_eq(td_sig, hexa_str("")))) {
            td_sig = hexa_str("void");
        }
        impl_parts = hexa_array_push(impl_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("typedef "), c_ret), hexa_str(" (*__ffi_ftyp_")), name), hexa_str(")(")), td_sig), hexa_str(");\n")));
        impl_parts = hexa_array_push(impl_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("static HexaVal "), name), hexa_str("(")), sig_p), hexa_str(") {\n")));
        HexaVal call_args = hexa_array_new();
        HexaVal ci = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ci); HexaVal __r=(nargs); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            call_args = hexa_array_push(call_args, gen2_ffi_marshal_arg(hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_106), ci), "name", &__hexa_codegen_c2_ic_107), hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_108), ci), "value", &__hexa_codegen_c2_ic_109)));
            ci = hexa_add(ci, hexa_int(1));
        }
        HexaVal call_str = hexa_str_join(call_args, hexa_str(", "));
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(ret_type, hexa_str("Void"))) || hexa_truthy(hexa_eq(ret_type, hexa_str("void"))))) || hexa_truthy(hexa_eq(ret_type, hexa_str("")))))) {
            impl_parts = hexa_array_push(impl_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    ((__ffi_ftyp_"), name), hexa_str(")__ffi_sym_")), name), hexa_str(")(")), call_str), hexa_str(");\n")));
            impl_parts = hexa_array_push(impl_parts, hexa_str("    return hexa_void();\n"));
        } else {
            impl_parts = hexa_array_push(impl_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    "), c_ret), hexa_str(" __r = ((__ffi_ftyp_")), name), hexa_str(")__ffi_sym_")), name), hexa_str(")(")), call_str), hexa_str(");\n")));
            impl_parts = hexa_array_push(impl_parts, hexa_add(hexa_add(hexa_str("    return "), gen2_ffi_wrap_ret(ret_type, hexa_str("__r"))), hexa_str(";\n")));
        }
        impl_parts = hexa_array_push(impl_parts, hexa_str("}\n"));
    } else {
        impl_parts = hexa_array_push(impl_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("static HexaVal "), name), hexa_str("(")), sig_p), hexa_str(") {\n")));
        impl_parts = hexa_array_push(impl_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    return hexa_extern_call(__ffi_sym_"), name), hexa_str(", NULL, 0, ")), gen2_extern_ret_kind(ret_type)), hexa_str(");\n")));
        impl_parts = hexa_array_push(impl_parts, hexa_str("}\n"));
    }
    HexaVal impl_code = hexa_str_join(impl_parts, hexa_str(""));
    HexaVal lib_arg = hexa_str("NULL");
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_110), hexa_str("")))))) {
        lib_arg = hexa_add(hexa_add(hexa_str("\""), hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_111)), hexa_str("\""));
    }
    HexaVal init = hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    __ffi_sym_"), name), hexa_str(" = hexa_ffi_dlsym(hexa_ffi_dlopen(")), lib_arg), hexa_str("), \"")), c_sym), hexa_str("\");\n"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "global", global), "forward", forward), "fn_code", impl_code), "init", init), "kind", hexa_str("")), "name", hexa_str("")), "value", hexa_str("")), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal gen2_indent(HexaVal n) {
    HexaVal parts = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(n); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        parts = hexa_array_push(parts, hexa_str("    "));
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal _gen2_has_decl(HexaVal name) {
    HexaVal n = hexa_int(hexa_len(_gen2_declared_names));
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(n); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(_gen2_declared_names, i), name))) {
            return hexa_bool(1);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal _gen2_collect_lets_stmt(HexaVal node, HexaVal names) {
    if (hexa_truthy(hexa_eq(hexa_type_of(node), hexa_str("string")))) {
        return names;
    }
    HexaVal sk = hexa_map_get_ic(node, "kind", &__hexa_codegen_c2_ic_112);
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(sk, hexa_str("LetStmt"))) || hexa_truthy(hexa_eq(sk, hexa_str("LetMutStmt")))))) {
        names = hexa_array_push(names, hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_113));
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "then_body", &__hexa_codegen_c2_ic_114)), hexa_str("string")))))) {
        names = _gen2_collect_lets(hexa_map_get_ic(node, "then_body", &__hexa_codegen_c2_ic_115), names);
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_116)), hexa_str("string")))))) {
        names = _gen2_collect_lets(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_117), names);
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_118)), hexa_str("string")))))) {
        names = _gen2_collect_lets(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_119), names);
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "arms", &__hexa_codegen_c2_ic_120)), hexa_str("string")))))) {
        HexaVal ai = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ai); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "arms", &__hexa_codegen_c2_ic_121)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal arm = hexa_index_get(hexa_map_get_ic(node, "arms", &__hexa_codegen_c2_ic_122), ai);
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(arm), hexa_str("string"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(arm, "body", &__hexa_codegen_c2_ic_123)), hexa_str("string")))))))) {
                names = _gen2_collect_lets(hexa_map_get_ic(arm, "body", &__hexa_codegen_c2_ic_124), names);
            }
            ai = hexa_add(ai, hexa_int(1));
        }
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(sk, hexa_str("ExprStmt"))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_125)), hexa_str("string")))))))) {
        names = _gen2_collect_lets_stmt(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_126), names);
    }
    return names;
    return hexa_void();
}


HexaVal _gen2_collect_lets(HexaVal stmts, HexaVal names) {
    if (hexa_truthy(hexa_eq(hexa_type_of(stmts), hexa_str("string")))) {
        return names;
    }
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(stmts))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        names = _gen2_collect_lets_stmt(hexa_index_get(stmts, i), names);
        i = hexa_add(i, hexa_int(1));
    }
    return names;
    return hexa_void();
}


HexaVal gen2_stmt(HexaVal node, HexaVal depth) {
    HexaVal val = hexa_void();
    HexaVal chunks = hexa_void();
    HexaVal ti = hexa_void();
    HexaVal fi = hexa_void();
    HexaVal pad2 = hexa_void();
    HexaVal pad = gen2_indent(depth);
    HexaVal k = hexa_map_get_ic(node, "kind", &__hexa_codegen_c2_ic_127);
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("LetStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("LetMutStmt")))))) {
        HexaVal init = hexa_str("hexa_void()");
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_128)), hexa_str("string")))))) {
            init = gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_129));
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("LetMutStmt"))) && hexa_truthy(hexa_eq(hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_130), hexa_str("__reg_promote__")))))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("register HexaVal ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_131)), hexa_str(" = ")), init), hexa_str("; /* reg-promoted */\n"));
        }
        if (hexa_truthy(_gen2_has_decl(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_132)))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_133)), hexa_str(" = ")), init), hexa_str(";\n"));
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("HexaVal ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_134)), hexa_str(" = ")), init), hexa_str(";\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ConstStmt")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("HexaVal ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_135)), hexa_str(" = ")), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_136))), hexa_str(";\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("AssignStmt")))) {
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_137)), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_138), "kind", &__hexa_codegen_c2_ic_139), hexa_str("Index")))))) {
            HexaVal container = gen2_expr(hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_140), "left", &__hexa_codegen_c2_ic_141));
            HexaVal idx = gen2_expr(hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_142), "right", &__hexa_codegen_c2_ic_143));
            val = gen2_expr(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_144));
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, container), hexa_str(" = hexa_index_set(")), container), hexa_str(", ")), idx), hexa_str(", ")), val), hexa_str(");\n"));
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_145)), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_146), "kind", &__hexa_codegen_c2_ic_147), hexa_str("Field")))))) {
            HexaVal obj = gen2_expr(hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_148), "left", &__hexa_codegen_c2_ic_149));
            HexaVal field = hexa_map_get_ic(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_150), "name", &__hexa_codegen_c2_ic_151);
            val = gen2_expr(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_152));
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, obj), hexa_str(" = hexa_map_set(")), obj), hexa_str(", \"")), field), hexa_str("\", ")), val), hexa_str(");\n"));
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(pad, gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_153))), hexa_str(" = ")), gen2_expr(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_154))), hexa_str(";\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("CompoundAssign")))) {
        HexaVal lhs = gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_155));
        HexaVal rhs = gen2_expr(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_156));
        HexaVal op = hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_157);
        if (hexa_truthy(hexa_eq(op, hexa_str("+=")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, lhs), hexa_str(" = hexa_add(")), lhs), hexa_str(", ")), rhs), hexa_str(");\n"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("-=")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, lhs), hexa_str(" = hexa_int((")), lhs), hexa_str(").i - (")), rhs), hexa_str(").i);\n"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("*=")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, lhs), hexa_str(" = hexa_int((")), lhs), hexa_str(").i * (")), rhs), hexa_str(").i);\n"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("/=")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, lhs), hexa_str(" = hexa_int((")), lhs), hexa_str(").i / (")), rhs), hexa_str(").i);\n"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("%=")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, lhs), hexa_str(" = hexa_int((")), lhs), hexa_str(").i % (")), rhs), hexa_str(").i);\n"));
        }
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("/* compound ")), op), hexa_str(" */\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ReturnStmt")))) {
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_158)), hexa_str("string")))))) {
            return hexa_add(hexa_add(hexa_add(pad, hexa_str("return ")), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_159))), hexa_str(";\n"));
        }
        return hexa_add(pad, hexa_str("return hexa_void();\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ExprStmt")))) {
        HexaVal expr = hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_160);
        if (hexa_truthy(hexa_eq(hexa_type_of(expr), hexa_str("string")))) {
            return hexa_str("");
        }
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(expr, "kind", &__hexa_codegen_c2_ic_161), hexa_str("MatchExpr")))) {
            return gen2_match_stmt(expr, depth);
        }
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(expr, "kind", &__hexa_codegen_c2_ic_162), hexa_str("IfExpr")))) {
            chunks = hexa_array_new();
            chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(pad, hexa_str("if (hexa_truthy(")), gen2_expr(hexa_map_get_ic(expr, "cond", &__hexa_codegen_c2_ic_163))), hexa_str(")) {\n")));
            ti = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ti); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(expr, "then_body", &__hexa_codegen_c2_ic_164)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(expr, "then_body", &__hexa_codegen_c2_ic_165), ti), hexa_add(depth, hexa_int(1))));
                ti = hexa_add(ti, hexa_int(1));
            }
            chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("}")));
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(expr, "else_body", &__hexa_codegen_c2_ic_166)), hexa_str("string"))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(hexa_map_get_ic(expr, "else_body", &__hexa_codegen_c2_ic_167)))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))))) {
                chunks = hexa_array_push(chunks, hexa_str(" else {\n"));
                HexaVal ei = hexa_int(0);
                while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ei); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(expr, "else_body", &__hexa_codegen_c2_ic_168)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                    chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(expr, "else_body", &__hexa_codegen_c2_ic_169), ei), hexa_add(depth, hexa_int(1))));
                    ei = hexa_add(ei, hexa_int(1));
                }
                chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("}")));
            }
            chunks = hexa_array_push(chunks, hexa_str("\n"));
            return hexa_str_join(chunks, hexa_str(""));
        }
        return hexa_add(hexa_add(pad, gen2_expr(expr)), hexa_str(";\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("WhileStmt")))) {
        chunks = hexa_array_new();
        chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(pad, hexa_str("while (hexa_truthy(")), gen2_expr(hexa_map_get_ic(node, "cond", &__hexa_codegen_c2_ic_170))), hexa_str(")) {\n")));
        HexaVal wi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(wi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_171)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_172), wi), hexa_add(depth, hexa_int(1))));
            wi = hexa_add(wi, hexa_int(1));
        }
        chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("}\n")));
        return hexa_str_join(chunks, hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ForStmt")))) {
        HexaVal iter = hexa_map_get_ic(node, "iter_expr", &__hexa_codegen_c2_ic_173);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(iter), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(iter, "kind", &__hexa_codegen_c2_ic_174), hexa_str("Range")))))) {
            HexaVal s = gen2_expr(hexa_map_get_ic(iter, "left", &__hexa_codegen_c2_ic_175));
            HexaVal e = gen2_expr(hexa_map_get_ic(iter, "right", &__hexa_codegen_c2_ic_176));
            chunks = hexa_array_new();
            chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("for (HexaVal ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_177)), hexa_str(" = ")), s), hexa_str("; ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_178)), hexa_str(".i < hexa_as_num(")), e), hexa_str("); ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_179)), hexa_str(".i++) {\n")));
            fi = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_180)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_181), fi), hexa_add(depth, hexa_int(1))));
                fi = hexa_add(fi, hexa_int(1));
            }
            chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("}\n")));
            return hexa_str_join(chunks, hexa_str(""));
        }
        HexaVal iter_c = gen2_expr(iter);
        chunks = hexa_array_new();
        chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("{\n")));
        pad2 = gen2_indent(hexa_add(depth, hexa_int(1)));
        chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(pad2, hexa_str("HexaVal __iter_arr = ")), iter_c), hexa_str(";\n")));
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("for (int __fi = 0; __fi < hexa_len(__iter_arr); __fi++) {\n")));
        HexaVal pad3 = gen2_indent(hexa_add(depth, hexa_int(2)));
        chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(pad3, hexa_str("HexaVal ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_182)), hexa_str(" = hexa_iter_get(__iter_arr, __fi);\n")));
        fi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_183)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_184), fi), hexa_add(depth, hexa_int(2))));
            fi = hexa_add(fi, hexa_int(1));
        }
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("}\n")));
        chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("}\n")));
        return hexa_str_join(chunks, hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BreakStmt")))) {
        return hexa_add(pad, hexa_str("break;\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ContinueStmt")))) {
        return hexa_add(pad, hexa_str("continue;\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("AssertStmt")))) {
        return hexa_add(hexa_add(hexa_add(pad, hexa_str("if (!hexa_truthy(")), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_185))), hexa_str(")) { fprintf(stderr, \"assertion failed\\n\"); exit(1); }\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ThrowStmt")))) {
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_186)), hexa_str("string")))))) {
            return hexa_add(hexa_add(hexa_add(pad, hexa_str("hexa_throw(")), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_187))), hexa_str(");\n"));
        }
        return hexa_add(pad, hexa_str("hexa_throw(hexa_str(\"error\"));\n"));
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("TryCatchStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("TryCatch")))))) {
        HexaVal try_body = hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_188);
        HexaVal catch_body = hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_189);
        HexaVal catch_var = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_190);
        chunks = hexa_array_new();
        chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("{\n")));
        pad2 = gen2_indent(hexa_add(depth, hexa_int(1)));
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("jmp_buf __jb; HexaVal __err = hexa_void();\n")));
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("if (setjmp(__jb) == 0) {\n")));
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("    __hexa_try_push(&__jb);\n")));
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(try_body), hexa_str("string")))))) {
            ti = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ti); HexaVal __r=(hexa_int(hexa_len(try_body))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(try_body, ti), hexa_add(depth, hexa_int(2))));
                ti = hexa_add(ti, hexa_int(1));
            }
        }
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("    __hexa_try_pop();\n")));
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("} else {\n")));
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("    __err = __hexa_last_error();\n")));
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(catch_var, hexa_str(""))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(catch_var, hexa_str("_")))))))) {
            chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(pad2, hexa_str("    HexaVal ")), catch_var), hexa_str(" = __err;\n")));
        }
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(catch_body), hexa_str("string")))))) {
            HexaVal ci = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ci); HexaVal __r=(hexa_int(hexa_len(catch_body))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(catch_body, ci), hexa_add(depth, hexa_int(2))));
                ci = hexa_add(ci, hexa_int(1));
            }
        }
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("}\n")));
        chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("}\n")));
        return hexa_str_join(chunks, hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("MatchExpr")))) {
        return gen2_match_stmt(node, depth);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("LoopStmt")))) {
        chunks = hexa_array_new();
        chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("while (1) {\n")));
        HexaVal li = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(li); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_191)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_192), li), hexa_add(depth, hexa_int(1))));
            li = hexa_add(li, hexa_int(1));
        }
        chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("}\n")));
        return hexa_str_join(chunks, hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("GuardStmt")))) {
        chunks = hexa_array_new();
        chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(pad, hexa_str("if (!hexa_truthy(")), gen2_expr(hexa_map_get_ic(node, "cond", &__hexa_codegen_c2_ic_193))), hexa_str(")) {\n")));
        HexaVal gi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(gi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_194)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_195), gi), hexa_add(depth, hexa_int(1))));
            gi = hexa_add(gi, hexa_int(1));
        }
        chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("}\n")));
        return hexa_str_join(chunks, hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("GuardLetStmt")))) {
        chunks = hexa_array_new();
        chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("HexaVal ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_196)), hexa_str(" = ")), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_197))), hexa_str(";\n")));
        chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(pad, hexa_str("if (!hexa_truthy(")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_198)), hexa_str(")) {\n")));
        HexaVal gli = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(gli); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_199)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_200), gli), hexa_add(depth, hexa_int(1))));
            gli = hexa_add(gli, hexa_int(1));
        }
        chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("}\n")));
        return hexa_str_join(chunks, hexa_str(""));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("InvariantDecl")))) {
        return hexa_str("");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("ComptimeConst")))) {
        HexaVal _cc_local = comptime_eval(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_201));
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(_cc_local), hexa_str("string")))))) {
            _register_comptime_const(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_202), _cc_local);
            return hexa_str("");
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(pad, hexa_str("HexaVal ")), hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_203)), hexa_str(" = ")), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_204))), hexa_str(";\n"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("OptimizeFnStmt")))) {
        return hexa_str("");
    }
    (hexa_eprint_val(hexa_add(hexa_str("[codegen_c2] ERROR: unhandled statement kind: "), k)), fprintf(stderr, "\n"), hexa_void());
    return hexa_add(hexa_add(hexa_add(pad, hexa_str("fprintf(stderr, \"CODEGEN ERROR: unhandled stmt kind: ")), k), hexa_str("\\n\"); exit(1);\n"));
    return hexa_void();
}


HexaVal c_escape(HexaVal s) {
    HexaVal out = hexa_str_replace(hexa_to_string(s), hexa_str("\\"), hexa_str("\\\\"));
    out = hexa_str_replace(out, hexa_str("\""), hexa_str("\\\""));
    out = hexa_str_replace(out, hexa_str("\n"), hexa_str("\\n"));
    out = hexa_str_replace(out, hexa_str("\r"), hexa_str("\\r"));
    out = hexa_str_replace(out, hexa_str("\t"), hexa_str("\\t"));
    return out;
    return hexa_void();
}


HexaVal gen2_method_builtin(HexaVal obj_expr, HexaVal method, HexaVal args) {
    if (hexa_truthy(hexa_eq(method, hexa_str("push")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_push("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("len")))) {
        return hexa_add(hexa_add(hexa_str("hexa_int(hexa_len("), obj_expr), hexa_str("))"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("chars")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str_chars("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("contains")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_str_contains("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str("))"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("join")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_join("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("to_upper")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str_to_upper("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("to_lower")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str_to_lower("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("split")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_split("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("trim")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str_trim("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("replace")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_replace("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(1)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("repeat")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_repeat("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("starts_with")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_str_starts_with("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str("))"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("ends_with")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_str_ends_with("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str("))"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("substring")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_substring("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(1)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("index_of")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_int(hexa_str_index_of("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str("))"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("keys")))) {
        return hexa_add(hexa_add(hexa_str("hexa_map_keys("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("values")))) {
        return hexa_add(hexa_add(hexa_str("hexa_map_values("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("contains_key")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_map_contains_key("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(".s))"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("remove")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_map_remove("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(".s)"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("pop")))) {
        return hexa_add(hexa_add(hexa_str("hexa_array_pop("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("reverse")))) {
        return hexa_add(hexa_add(hexa_str("hexa_array_reverse("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("sort")))) {
        return hexa_add(hexa_add(hexa_str("hexa_array_sort("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("truncate")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_truncate("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("push_nostat")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_push_nostat("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("trim_start")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str_trim_start("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("trim_end")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str_trim_end("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("slice")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_slice("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(1)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("slice_fast")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_slice_fast("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(1)))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("to_string")))) {
        return hexa_add(hexa_add(hexa_str("hexa_to_string("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("parse_int")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str_parse_int("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("parse_float")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str_parse_float("), obj_expr), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(method, hexa_str("pad_left")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_pad_left("), obj_expr), hexa_str(", ")), gen2_expr(hexa_index_get(args, hexa_int(0)))), hexa_str(")"));
    }
    (hexa_eprint_val(hexa_add(hexa_str("[codegen_c2] ERROR: unknown builtin method: "), method)), fprintf(stderr, "\n"), hexa_void());
    return hexa_add(hexa_add(hexa_str("(fprintf(stderr, \"CODEGEN ERROR: unknown builtin method: "), method), hexa_str("\\n\"), exit(1), hexa_void())"));
    return hexa_void();
}


HexaVal gen2_expr(HexaVal node) {
    HexaVal obj = hexa_void();
    HexaVal name = hexa_void();
    HexaVal arg_strs = hexa_void();
    HexaVal si = hexa_void();
    HexaVal a = hexa_void();
    HexaVal b = hexa_void();
    HexaVal a_strs = hexa_void();
    HexaVal n = hexa_void();
    HexaVal ai = hexa_void();
    HexaVal nargs = hexa_void();
    HexaVal ti = hexa_void();
    HexaVal out = hexa_void();
    HexaVal k = hexa_map_get_ic(node, "kind", &__hexa_codegen_c2_ic_205);
    if (hexa_truthy(hexa_eq(k, hexa_str("IntLit")))) {
        return hexa_add(hexa_add(hexa_str("hexa_int("), hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_206)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("FloatLit")))) {
        return hexa_add(hexa_add(hexa_str("hexa_float("), hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_207)), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BoolLit")))) {
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_208), hexa_str("true")))) {
            return hexa_str("hexa_bool(1)");
        }
        return hexa_str("hexa_bool(0)");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StringLit")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str(\""), c_escape(hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_209))), hexa_str("\")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("CharLit")))) {
        return hexa_add(hexa_add(hexa_str("hexa_str(\""), c_escape(hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_210))), hexa_str("\")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Ident")))) {
        HexaVal _cc_inline = _lookup_comptime_const(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_211));
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(_cc_inline), hexa_str("string")))))) {
            return gen2_expr(_cc_inline);
        }
        return _hexa_mangle_ident(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_212));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BinOp")))) {
        HexaVal l = gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_213));
        HexaVal r = gen2_expr(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_214));
        HexaVal op = hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_215);
        if (hexa_truthy(hexa_eq(op, hexa_str("+")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_add("), l), hexa_str(", ")), r), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("-")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_sub("), l), hexa_str(", ")), r), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("*")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_mul("), l), hexa_str(", ")), r), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("/")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_div("), l), hexa_str(", ")), r), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("%")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_mod("), l), hexa_str(", ")), r), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("==")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_eq("), l), hexa_str(", ")), r), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("!=")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(!hexa_truthy(hexa_eq("), l), hexa_str(", ")), r), hexa_str(")))"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("<")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(__extension__ ({ HexaVal __l=("), l), hexa_str("); HexaVal __r=(")), r), hexa_str("); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str(">")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(__extension__ ({ HexaVal __l=("), l), hexa_str("); HexaVal __r=(")), r), hexa_str("); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); }))"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("<=")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(__extension__ ({ HexaVal __l=("), l), hexa_str("); HexaVal __r=(")), r), hexa_str("); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) <= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i <= __r.i); }))"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str(">=")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(__extension__ ({ HexaVal __l=("), l), hexa_str("); HexaVal __r=(")), r), hexa_str("); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); }))"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("&&")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_truthy("), l), hexa_str(") && hexa_truthy(")), r), hexa_str("))"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("||")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_truthy("), l), hexa_str(") || hexa_truthy(")), r), hexa_str("))"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("&")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_int(("), l), hexa_str(").i & (")), r), hexa_str(").i)"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("^")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_int(("), l), hexa_str(").i ^ (")), r), hexa_str(").i)"));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("??")))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_null_coal("), l), hexa_str(", ")), r), hexa_str(")"));
        }
        (hexa_eprint_val(hexa_add(hexa_str("[codegen_c2] ERROR: unhandled binary operator: "), op)), fprintf(stderr, "\n"), hexa_void());
        return hexa_add(hexa_add(hexa_str("(fprintf(stderr, \"CODEGEN ERROR: unhandled binop: "), op), hexa_str("\\n\"), exit(1), hexa_void())"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("UnaryOp")))) {
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_216), hexa_str("-")))) {
            return hexa_add(hexa_add(hexa_str("hexa_sub(hexa_int(0), "), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_217))), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_218), hexa_str("!")))) {
            return hexa_add(hexa_add(hexa_str("hexa_bool(!hexa_truthy("), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_219))), hexa_str("))"));
        }
        (hexa_eprint_val(hexa_add(hexa_str("[codegen_c2] ERROR: unhandled unary operator: "), hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_220))), fprintf(stderr, "\n"), hexa_void());
        return hexa_add(hexa_add(hexa_str("(fprintf(stderr, \"CODEGEN ERROR: unhandled unary op: "), hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_221)), hexa_str("\\n\"), exit(1), hexa_void())"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Field")))) {
        obj = gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_222));
        HexaVal field = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_223);
        HexaVal id = _ic_counter;
        _ic_counter = hexa_add(_ic_counter, hexa_int(1));
        HexaVal slot = hexa_add(hexa_add(hexa_str("__hexa"), hexa_str("_ic_")), hexa_to_string(id));
        _ic_def_parts = hexa_array_push(_ic_def_parts, hexa_add(hexa_add(hexa_str("static HexaIC "), slot), hexa_str(" = {0};\n")));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_map_get_ic("), obj), hexa_str(", \"")), field), hexa_str("\", &")), slot), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StructInit")))) {
        name = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_224);
        arg_strs = hexa_array_new();
        si = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(si); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_225)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            arg_strs = hexa_array_push(arg_strs, gen2_expr(hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_226), si), "left", &__hexa_codegen_c2_ic_227)));
            si = hexa_add(si, hexa_int(1));
        }
        return hexa_add(hexa_add(hexa_add(name, hexa_str("(")), hexa_str_join(arg_strs, hexa_str(", "))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Call")))) {
        HexaVal callee = hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_228);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(callee), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(callee, "kind", &__hexa_codegen_c2_ic_229), hexa_str("Ident")))))) {
            name = hexa_map_get_ic(callee, "name", &__hexa_codegen_c2_ic_230);
            if (hexa_truthy(hexa_eq(name, hexa_str("println")))) {
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_231)))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                    return hexa_add(hexa_add(hexa_str("hexa_println("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_232), hexa_int(0)))), hexa_str(")"));
                }
                return hexa_str("(printf(\"\\n\"), hexa_void())");
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("print")))) {
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_233)))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                    return hexa_add(hexa_add(hexa_str("(hexa_print_val("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_234), hexa_int(0)))), hexa_str("), hexa_void())"));
                }
                return hexa_str("hexa_void()");
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("len")))) {
                return hexa_add(hexa_add(hexa_str("hexa_int(hexa_len("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_235), hexa_int(0)))), hexa_str("))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("to_string")))) {
                return hexa_add(hexa_add(hexa_str("hexa_to_string("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_236), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("type_of")))) {
                return hexa_add(hexa_add(hexa_str("hexa_type_of("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_237), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("sqrt")))) {
                return hexa_add(hexa_add(hexa_str("hexa_sqrt("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_238), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("floor")))) {
                return hexa_add(hexa_add(hexa_str("hexa_floor("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_239), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ceil")))) {
                return hexa_add(hexa_add(hexa_str("hexa_ceil("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_240), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("abs")))) {
                return hexa_add(hexa_add(hexa_str("hexa_abs("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_241), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("round")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_242), hexa_int(0)));
                return hexa_add(hexa_add(hexa_str("hexa_int((int64_t)round(__hx_to_double("), a), hexa_str(")))"));
            }
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(name, hexa_str("ln"))) || hexa_truthy(hexa_eq(name, hexa_str("log")))))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_243), hexa_int(0)));
                return hexa_add(hexa_add(hexa_str("hexa_float(log(__hx_to_double("), a), hexa_str(")))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("log10")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_244), hexa_int(0)));
                return hexa_add(hexa_add(hexa_str("hexa_float(log10(__hx_to_double("), a), hexa_str(")))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("exp")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_245), hexa_int(0)));
                return hexa_add(hexa_add(hexa_str("hexa_float(exp(__hx_to_double("), a), hexa_str(")))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("sin")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_246), hexa_int(0)));
                return hexa_add(hexa_add(hexa_str("hexa_float(sin(__hx_to_double("), a), hexa_str(")))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("cos")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_247), hexa_int(0)));
                return hexa_add(hexa_add(hexa_str("hexa_float(cos(__hx_to_double("), a), hexa_str(")))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("pow")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_pow("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_248), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_249), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("to_float")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_250), hexa_int(0)));
                return hexa_add(hexa_add(hexa_str("hexa_float(__hx_to_double("), a), hexa_str("))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("is_alpha")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_251), hexa_int(0)));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(("), a), hexa_str(".tag==TAG_STR && ")), a), hexa_str(".s && isalpha((unsigned char)")), a), hexa_str(".s[0])) || (")), a), hexa_str(".tag==TAG_CHAR && isalpha((unsigned char)")), a), hexa_str(".i)))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("is_digit")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_252), hexa_int(0)));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(("), a), hexa_str(".tag==TAG_STR && ")), a), hexa_str(".s && isdigit((unsigned char)")), a), hexa_str(".s[0])) || (")), a), hexa_str(".tag==TAG_CHAR && isdigit((unsigned char)")), a), hexa_str(".i)))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("is_alphanumeric")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_253), hexa_int(0)));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(("), a), hexa_str(".tag==TAG_STR && ")), a), hexa_str(".s && isalnum((unsigned char)")), a), hexa_str(".s[0])) || (")), a), hexa_str(".tag==TAG_CHAR && isalnum((unsigned char)")), a), hexa_str(".i)))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("file_exists")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_254), hexa_int(0)));
                return hexa_add(hexa_add(hexa_str("hexa_bool(access("), a), hexa_str(".s, F_OK) == 0)"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("format")))) {
                HexaVal fmt_args = hexa_str("hexa_array_new()");
                HexaVal fi = hexa_int(1);
                while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_255)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                    fmt_args = hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_push("), fmt_args), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_256), fi))), hexa_str(")"));
                    fi = hexa_add(fi, hexa_int(1));
                }
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_format_n("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_257), hexa_int(0)))), hexa_str(", ")), fmt_args), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("eprintln")))) {
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_258)))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                    return hexa_add(hexa_add(hexa_str("(hexa_eprint_val("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_259), hexa_int(0)))), hexa_str("), fprintf(stderr, \"\\n\"), hexa_void())"));
                }
                return hexa_str("(fprintf(stderr, \"\\n\"), hexa_void())");
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("args")))) {
                return hexa_str("hexa_args()");
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("exec")))) {
                return hexa_add(hexa_add(hexa_str("hexa_exec("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_260), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("to_int")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_261), hexa_int(0)));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_int(("), a), hexa_str(".tag==TAG_STR?atoll(hexa_to_cstring(")), a), hexa_str(")):(int64_t)__hx_to_double(")), a), hexa_str(")))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("min")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_262), hexa_int(0)));
                b = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_263), hexa_int(1)));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_int(hexa_as_num("), a), hexa_str(") < hexa_as_num(")), b), hexa_str(") ? hexa_as_num(")), a), hexa_str(") : hexa_as_num(")), b), hexa_str("))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("max")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_264), hexa_int(0)));
                b = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_265), hexa_int(1)));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_int(hexa_as_num("), a), hexa_str(") > hexa_as_num(")), b), hexa_str(") ? hexa_as_num(")), a), hexa_str(") : hexa_as_num(")), b), hexa_str("))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("read_file")))) {
                return hexa_add(hexa_add(hexa_str("hexa_read_file("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_266), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("write_file")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_write_file("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_267), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_268), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("cstring")))) {
                return hexa_add(hexa_add(hexa_str("hexa_cstring("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_269), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("from_cstring")))) {
                return hexa_add(hexa_add(hexa_str("hexa_from_cstring("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_270), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_null")))) {
                return hexa_str("hexa_ptr_null()");
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_addr")))) {
                return hexa_add(hexa_add(hexa_str("hexa_ptr_addr("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_271), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("callback_create")))) {
                HexaVal arg = hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_272), hexa_int(0));
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(arg), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(arg, "kind", &__hexa_codegen_c2_ic_273), hexa_str("Ident")))))) {
                    HexaVal fn_name = hexa_map_get_ic(arg, "name", &__hexa_codegen_c2_ic_274);
                    return hexa_add(hexa_add(hexa_str("hexa_callback_create((HexaVal){.tag=TAG_FN, .fn={.fn_ptr=(void*)"), fn_name), hexa_str(", .arity=0}})"));
                }
                return hexa_add(hexa_add(hexa_str("hexa_callback_create("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_275), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("callback_free")))) {
                return hexa_add(hexa_add(hexa_str("hexa_callback_free("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_276), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("callback_slot_id")))) {
                return hexa_add(hexa_add(hexa_str("hexa_callback_slot_id("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_277), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_alloc")))) {
                return hexa_add(hexa_add(hexa_str("hexa_ptr_alloc("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_278), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_free")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_free("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_279), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_280), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_write")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_write("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_281), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_282), hexa_int(1)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_283), hexa_int(2)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_write_f32")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_write_f32("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_284), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_285), hexa_int(1)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_286), hexa_int(2)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_write_i32")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_write_i32("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_287), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_288), hexa_int(1)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_289), hexa_int(2)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_read")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_read("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_290), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_291), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_read_f64")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_read_f64("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_292), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_293), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_read_f32")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_read_f32("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_294), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_295), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_read_i32")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_read_i32("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_296), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_297), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_offset")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_offset("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_298), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_299), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("deref")))) {
                return hexa_add(hexa_add(hexa_str("hexa_deref("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_300), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("__prefetch")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_301), hexa_int(0)));
                b = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_302), hexa_int(1)));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("(__builtin_prefetch(hexa_to_cstring(hexa_index("), a), hexa_str(", hexa_int(hexa_as_num(")), b), hexa_str(") + 1))), 0, 3), hexa_void())"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("struct_pack")))) {
                a_strs = hexa_array_new();
                si = hexa_int(0);
                while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(si); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_303)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                    a_strs = hexa_array_push(a_strs, gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_304), si)));
                    si = hexa_add(si, hexa_int(1));
                }
                n = hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_305))));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_struct_pack((HexaVal[]){"), hexa_str_join(a_strs, hexa_str(", "))), hexa_str("}, ")), n), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("struct_pack_f32")))) {
                a_strs = hexa_array_new();
                si = hexa_int(0);
                while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(si); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_306)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                    a_strs = hexa_array_push(a_strs, gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_307), si)));
                    si = hexa_add(si, hexa_int(1));
                }
                n = hexa_to_string(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_308))));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_struct_pack_f32((HexaVal[]){"), hexa_str_join(a_strs, hexa_str(", "))), hexa_str("}, ")), n), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("struct_unpack")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_struct_unpack("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_309), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_310), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("struct_unpack_f32")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_struct_unpack_f32("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_311), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_312), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("struct_rect")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_struct_rect("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_313), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_314), hexa_int(1)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_315), hexa_int(2)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_316), hexa_int(3)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("struct_point")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_struct_point("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_317), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_318), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("struct_size")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_struct_size_pack("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_319), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_320), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("struct_free")))) {
                return hexa_add(hexa_add(hexa_str("hexa_struct_free("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_321), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("alloc_raw")))) {
                return hexa_add(hexa_add(hexa_str("hexa_ptr_alloc("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_322), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("free_raw")))) {
                return hexa_add(hexa_add(hexa_str("hexa_ptr_free("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_323), hexa_int(0)))), hexa_str(", hexa_int(0))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("write_f32")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_write_f32("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_324), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_325), hexa_int(1)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_326), hexa_int(2)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("write_i32")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_write_i32("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_327), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_328), hexa_int(1)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_329), hexa_int(2)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("write_i64")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_write("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_330), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_331), hexa_int(1)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_332), hexa_int(2)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("deref_f32")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_read_f32("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_333), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_334), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("deref_i32")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_ptr_read_i32("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_335), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_336), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("ptr_from_int")))) {
                return gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_337), hexa_int(0)));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("int")))) {
                a = gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_338), hexa_int(0)));
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_int(("), a), hexa_str(".tag==TAG_STR?atoll(hexa_to_cstring(")), a), hexa_str(")):(int64_t)__hx_to_double(")), a), hexa_str(")))"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("str")))) {
                return hexa_add(hexa_add(hexa_str("hexa_to_string("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_339), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("clock")))) {
                return hexa_str("hexa_clock()");
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("random")))) {
                return hexa_str("hexa_random()");
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("tensor")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_tensor_new("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_340), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_341), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("randn")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_tensor_randn("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_342), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_343), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("tensor_data_f32_ptr")))) {
                return hexa_add(hexa_add(hexa_str("hexa_tensor_data_ptr("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_344), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(name, hexa_str("tensor_from_f32_ptr")))) {
                /* 2026-04-16 CUDA-compose spike fix: accept both 2-arg (ptr, numel)
                   and 3-arg (ptr, rows, cols) forms. cuda_ffi.hexa / gpu_train.hexa
                   use the 2-arg flat-vector form. */
                if (hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_345)) == 2) {
                    return hexa_add(hexa_add(hexa_add(hexa_str("hexa_tensor_from_ptr("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_345), hexa_int(0)))), hexa_str(", hexa_int(1), ")), hexa_add(gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_346), hexa_int(1))), hexa_str(")")));
                }
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_tensor_from_ptr("), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_345), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_346), hexa_int(1)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_347), hexa_int(2)))), hexa_str(")"));
            }
            arg_strs = hexa_array_new();
            ai = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ai); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_348)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                arg_strs = hexa_array_push(arg_strs, gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_349), ai)));
                ai = hexa_add(ai, hexa_int(1));
            }
            if (hexa_truthy(_is_known_fn_global(name))) {
                return hexa_add(hexa_add(hexa_add(_hexa_mangle_ident(name), hexa_str("(")), hexa_str_join(arg_strs, hexa_str(", "))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_350)))); HexaVal __r=(hexa_int(2)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
                if (hexa_truthy(hexa_eq(name, hexa_str("contains")))) {
                    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_str_contains("), hexa_index_get(arg_strs, hexa_int(0))), hexa_str(", ")), hexa_index_get(arg_strs, hexa_int(1))), hexa_str("))"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("starts_with")))) {
                    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_str_starts_with("), hexa_index_get(arg_strs, hexa_int(0))), hexa_str(", ")), hexa_index_get(arg_strs, hexa_int(1))), hexa_str("))"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("ends_with")))) {
                    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_str_ends_with("), hexa_index_get(arg_strs, hexa_int(0))), hexa_str(", ")), hexa_index_get(arg_strs, hexa_int(1))), hexa_str("))"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("join")))) {
                    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_join("), hexa_index_get(arg_strs, hexa_int(0))), hexa_str(", ")), hexa_index_get(arg_strs, hexa_int(1))), hexa_str(")"));
                }
            }
            if (hexa_truthy(hexa_eq(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_351))), hexa_int(0)))) {
                if (hexa_truthy(hexa_eq(name, hexa_str("timestamp")))) {
                    return hexa_str("hexa_timestamp()");
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("input")))) {
                    return hexa_str("hexa_input(hexa_str(\"\"))");
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("random")))) {
                    return hexa_str("hexa_random()");
                }
            }
            if (hexa_truthy(hexa_eq(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_352))), hexa_int(1)))) {
                HexaVal a0 = hexa_index_get(arg_strs, hexa_int(0));
                if (hexa_truthy(hexa_eq(name, hexa_str("exit")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_exit("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("sleep")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_sleep("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("tanh")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_math_tanh("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("sin")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_math_sin("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("cos")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_math_cos("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("tan")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_math_tan("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("asin")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_math_asin("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("acos")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_math_acos("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("atan")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_math_atan("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("log")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_math_log("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("exp")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_math_exp("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("input")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_input("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("is_error")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_is_error("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("read_lines")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_read_lines("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("from_char_code")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_from_char_code("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("env_var")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_env_var("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("delete_file")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_delete_file("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("bin")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_bin("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("hex")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_hex("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("base64_encode")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_base64_encode("), a0), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("base64_decode")))) {
                    return hexa_add(hexa_add(hexa_str("hexa_base64_decode("), a0), hexa_str(")"));
                }
            }
            if (hexa_truthy(hexa_eq(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_353))), hexa_int(2)))) {
                if (hexa_truthy(hexa_eq(name, hexa_str("append_file")))) {
                    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_append_file("), hexa_index_get(arg_strs, hexa_int(0))), hexa_str(", ")), hexa_index_get(arg_strs, hexa_int(1))), hexa_str(")"));
                }
                if (hexa_truthy(hexa_eq(name, hexa_str("atan2")))) {
                    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_math_atan2("), hexa_index_get(arg_strs, hexa_int(0))), hexa_str(", ")), hexa_index_get(arg_strs, hexa_int(1))), hexa_str(")"));
                }
            }
            nargs = hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_354)));
            if (hexa_truthy(hexa_eq(nargs, hexa_int(0)))) {
                return hexa_add(hexa_add(hexa_str("hexa_call0("), name), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(nargs, hexa_int(1)))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_call1("), name), hexa_str(", ")), hexa_index_get(arg_strs, hexa_int(0))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(nargs, hexa_int(2)))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_call2("), name), hexa_str(", ")), hexa_str_join(arg_strs, hexa_str(", "))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(nargs, hexa_int(3)))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_call3("), name), hexa_str(", ")), hexa_str_join(arg_strs, hexa_str(", "))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(nargs, hexa_int(4)))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_call4("), name), hexa_str(", ")), hexa_str_join(arg_strs, hexa_str(", "))), hexa_str(")"));
            }
            return hexa_add(hexa_add(hexa_add(name, hexa_str("(")), hexa_str_join(arg_strs, hexa_str(", "))), hexa_str(")"));
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(callee), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(callee, "kind", &__hexa_codegen_c2_ic_355), hexa_str("Field")))))) {
            obj = gen2_expr(hexa_map_get_ic(callee, "left", &__hexa_codegen_c2_ic_356));
            HexaVal method = hexa_map_get_ic(callee, "name", &__hexa_codegen_c2_ic_357);
            HexaVal user_types = _method_registry_lookup(method);
            if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(user_types))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                HexaVal u_args = hexa_array_new();
                HexaVal uai = hexa_int(0);
                while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(uai); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_358)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                    u_args = hexa_array_push(u_args, gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_359), uai)));
                    uai = hexa_add(uai, hexa_int(1));
                }
                HexaVal u_arg_tail = hexa_str_join(u_args, hexa_str(", "));
                HexaVal __saved_obj = obj;
                HexaVal fb = gen2_method_builtin(hexa_str("__mr"), method, hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_360));
                HexaVal chain = fb;
                ti = hexa_sub(hexa_int(hexa_len(user_types)), hexa_int(1));
                while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ti); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
                    HexaVal tname = hexa_index_get(user_types, ti);
                    HexaVal call_args = hexa_str("__mr");
                    HexaVal full_args = (hexa_truthy(hexa_eq(u_arg_tail, hexa_str(""))) ? call_args : hexa_add(hexa_add(call_args, hexa_str(", ")), u_arg_tail));
                    chain = hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("(hexa_is_type(__mr, \""), tname), hexa_str("\") ? ")), tname), hexa_str("__")), method), hexa_str("(")), full_args), hexa_str(") : ")), chain), hexa_str(")"));
                    ti = hexa_sub(ti, hexa_int(1));
                }
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("({ HexaVal __mr = "), __saved_obj), hexa_str("; ")), chain), hexa_str("; })"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("push")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_push("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_361), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("len")))) {
                return hexa_add(hexa_add(hexa_str("hexa_int(hexa_len("), obj), hexa_str("))"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("chars")))) {
                return hexa_add(hexa_add(hexa_str("hexa_str_chars("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("contains")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_str_contains("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_362), hexa_int(0)))), hexa_str("))"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("join")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_join("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_363), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("to_upper")))) {
                return hexa_add(hexa_add(hexa_str("hexa_str_to_upper("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("to_lower")))) {
                return hexa_add(hexa_add(hexa_str("hexa_str_to_lower("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("split")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_split("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_364), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("trim")))) {
                return hexa_add(hexa_add(hexa_str("hexa_str_trim("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("replace")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_replace("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_365), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_366), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("repeat")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_repeat("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_367), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("starts_with")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_str_starts_with("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_368), hexa_int(0)))), hexa_str("))"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("ends_with")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_str_ends_with("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_369), hexa_int(0)))), hexa_str("))"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("substring")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_str_substring("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_370), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_371), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("index_of")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_int(hexa_str_index_of("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_372), hexa_int(0)))), hexa_str("))"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("keys")))) {
                return hexa_add(hexa_add(hexa_str("hexa_map_keys("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("values")))) {
                return hexa_add(hexa_add(hexa_str("hexa_map_values("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("contains_key")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_bool(hexa_map_contains_key("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_373), hexa_int(0)))), hexa_str(".s))"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("remove")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_map_remove("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_374), hexa_int(0)))), hexa_str(".s)"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("pop")))) {
                return hexa_add(hexa_add(hexa_str("hexa_array_pop("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("reverse")))) {
                return hexa_add(hexa_add(hexa_str("hexa_array_reverse("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("sort")))) {
                return hexa_add(hexa_add(hexa_str("hexa_array_sort("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("truncate")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_truncate("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_375), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("push_nostat")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_push_nostat("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_376), hexa_int(0)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("trim_start")))) {
                return hexa_add(hexa_add(hexa_str("hexa_str_trim_start("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("trim_end")))) {
                return hexa_add(hexa_add(hexa_str("hexa_str_trim_end("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("slice")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_slice("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_377), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_378), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("slice_fast")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_slice_fast("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_379), hexa_int(0)))), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_380), hexa_int(1)))), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("to_string")))) {
                return hexa_add(hexa_add(hexa_str("hexa_to_string("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("parse_int")))) {
                return hexa_add(hexa_add(hexa_str("hexa_str_parse_int("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("parse_float")))) {
                return hexa_add(hexa_add(hexa_str("hexa_str_parse_float("), obj), hexa_str(")"));
            }
            if (hexa_truthy(hexa_eq(method, hexa_str("pad_left")))) {
                return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_pad_left("), obj), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_381), hexa_int(0)))), hexa_str(")"));
            }
            (hexa_eprint_val(hexa_add(hexa_str("[codegen_c2] ERROR: unhandled method call: "), method)), fprintf(stderr, "\n"), hexa_void());
            return hexa_add(hexa_add(hexa_str("(fprintf(stderr, \"CODEGEN ERROR: unhandled method: "), method), hexa_str("\\n\"), exit(1), hexa_void())"));
        }
        HexaVal cexpr = gen2_expr(callee);
        nargs = hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_382)));
        HexaVal cargs = hexa_array_new();
        HexaVal ci = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ci); HexaVal __r=(nargs); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            cargs = hexa_array_push(cargs, gen2_expr(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_383), ci)));
            ci = hexa_add(ci, hexa_int(1));
        }
        if (hexa_truthy(hexa_eq(nargs, hexa_int(0)))) {
            return hexa_add(hexa_add(hexa_str("hexa_call0("), cexpr), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(nargs, hexa_int(1)))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_call1("), cexpr), hexa_str(", ")), hexa_index_get(cargs, hexa_int(0))), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(nargs, hexa_int(2)))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_call2("), cexpr), hexa_str(", ")), hexa_str_join(cargs, hexa_str(", "))), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(nargs, hexa_int(3)))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_call3("), cexpr), hexa_str(", ")), hexa_str_join(cargs, hexa_str(", "))), hexa_str(")"));
        }
        if (hexa_truthy(hexa_eq(nargs, hexa_int(4)))) {
            return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_call4("), cexpr), hexa_str(", ")), hexa_str_join(cargs, hexa_str(", "))), hexa_str(")"));
        }
        (hexa_eprint_val(hexa_add(hexa_add(hexa_str("[codegen_c2] ERROR: indirect call arity "), hexa_to_string(nargs)), hexa_str(" unsupported (max 4)"))), fprintf(stderr, "\n"), hexa_void());
        return hexa_add(hexa_add(hexa_str("(fprintf(stderr, \"CODEGEN ERROR: indirect call arity %d unsupported\\n\", "), hexa_to_string(nargs)), hexa_str("), exit(1), hexa_void())"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Array")))) {
        out = hexa_str("hexa_array_new()");
        ai = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ai); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_codegen_c2_ic_384)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            out = hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_push("), out), hexa_str(", ")), gen2_expr(hexa_index_get(hexa_map_get_ic(node, "items", &__hexa_codegen_c2_ic_385), ai))), hexa_str(")"));
            ai = hexa_add(ai, hexa_int(1));
        }
        return out;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Index")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_index_get("), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_386))), hexa_str(", ")), gen2_expr(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_387))), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("EnumPath")))) {
        HexaVal ename = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_388);
        HexaVal vname = hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_389);
        return hexa_add(hexa_add(ename, hexa_str("_")), vname);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("IfExpr")))) {
        HexaVal c = gen2_expr(hexa_map_get_ic(node, "cond", &__hexa_codegen_c2_ic_390));
        HexaVal t_val = hexa_str("hexa_void()");
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "then_body", &__hexa_codegen_c2_ic_391)), hexa_str("string"))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(hexa_map_get_ic(node, "then_body", &__hexa_codegen_c2_ic_392)))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))))) {
            HexaVal t_last = hexa_index_get(hexa_map_get_ic(node, "then_body", &__hexa_codegen_c2_ic_393), hexa_sub(hexa_int(hexa_len(hexa_map_get_ic(node, "then_body", &__hexa_codegen_c2_ic_394))), hexa_int(1)));
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(t_last), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(t_last, "kind", &__hexa_codegen_c2_ic_395), hexa_str("ExprStmt"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(t_last, "left", &__hexa_codegen_c2_ic_396)), hexa_str("string")))))))) {
                t_val = gen2_expr(hexa_map_get_ic(t_last, "left", &__hexa_codegen_c2_ic_397));
            }
        }
        HexaVal e_val = hexa_str("hexa_void()");
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_398)), hexa_str("string"))))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_399)))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))))) {
            HexaVal e_last = hexa_index_get(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_400), hexa_sub(hexa_int(hexa_len(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_401))), hexa_int(1)));
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(e_last), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(e_last, "kind", &__hexa_codegen_c2_ic_402), hexa_str("ExprStmt"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(e_last, "left", &__hexa_codegen_c2_ic_403)), hexa_str("string")))))))) {
                e_val = gen2_expr(hexa_map_get_ic(e_last, "left", &__hexa_codegen_c2_ic_404));
            }
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("(hexa_truthy("), c), hexa_str(") ? ")), t_val), hexa_str(" : ")), e_val), hexa_str(")"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("MatchExpr")))) {
        return gen2_match_expr(node);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Lambda")))) {
        return gen2_lambda_expr(node);
    }
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("Tuple"))) || hexa_truthy(hexa_eq(k, hexa_str("TupleLit")))))) {
        out = hexa_str("hexa_array_new()");
        HexaVal items = hexa_map_get_ic(node, "items", &__hexa_codegen_c2_ic_405);
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(items), hexa_str("string")))))) {
            ti = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ti); HexaVal __r=(hexa_int(hexa_len(items))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                out = hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_push("), out), hexa_str(", ")), gen2_expr(hexa_index_get(items, ti))), hexa_str(")"));
                ti = hexa_add(ti, hexa_int(1));
            }
        }
        return out;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("MapLit")))) {
        out = hexa_str("hexa_map_new()");
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "items", &__hexa_codegen_c2_ic_406)), hexa_str("string")))))) {
            HexaVal mi = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(mi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_codegen_c2_ic_407)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                HexaVal entry = hexa_index_get(hexa_map_get_ic(node, "items", &__hexa_codegen_c2_ic_408), mi);
                HexaVal key_c = gen2_expr(hexa_map_get_ic(entry, "left", &__hexa_codegen_c2_ic_409));
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(entry, "left", &__hexa_codegen_c2_ic_410)), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_map_get_ic(entry, "left", &__hexa_codegen_c2_ic_411), "kind", &__hexa_codegen_c2_ic_412), hexa_str("StringLit")))))) {
                    key_c = hexa_add(hexa_add(hexa_str("\""), c_escape(hexa_map_get_ic(hexa_map_get_ic(entry, "left", &__hexa_codegen_c2_ic_413), "value", &__hexa_codegen_c2_ic_414))), hexa_str("\""));
                }
                out = hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_map_set("), out), hexa_str(", ")), key_c), hexa_str(", ")), gen2_expr(hexa_map_get_ic(entry, "right", &__hexa_codegen_c2_ic_415))), hexa_str(")"));
                mi = hexa_add(mi, hexa_int(1));
            }
        }
        return out;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("NegFloat")))) {
        return hexa_add(hexa_add(hexa_str("hexa_float(-("), gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_416))), hexa_str(").f)"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Wildcard")))) {
        return hexa_str("/* wildcard */");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("")))) {
        return hexa_str("hexa_map_new()");
    }
    (hexa_eprint_val(hexa_add(hexa_str("[codegen_c2] ERROR: unhandled expression kind: "), k)), fprintf(stderr, "\n"), hexa_void());
    return hexa_add(hexa_add(hexa_str("(fprintf(stderr, \"CODEGEN ERROR: unhandled expr kind: "), k), hexa_str("\\n\"), exit(1), hexa_void())"));
    return hexa_void();
}


HexaVal gen2_stack_alloc_struct(HexaVal var_name, HexaVal fields) {
    HexaVal parts = hexa_array_new();
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("    // [escape-analysis] stack-promoted: "), var_name), hexa_str("\n")));
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("    HexaVal "), var_name), hexa_str(" = hexa_map_new(); // stack-eligible\n")));
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(fields))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal f = hexa_index_get(fields, i);
        parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    "), var_name), hexa_str(" = hexa_map_set(")), var_name), hexa_str(", \"")), f), hexa_str("\", hexa_void());\n")));
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_stack_alloc_array(HexaVal var_name, HexaVal size_hint) {
    HexaVal parts = hexa_array_new();
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    // [escape-analysis] stack array: "), var_name), hexa_str(" (size hint: ")), hexa_to_string(size_hint)), hexa_str(")\n")));
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("    HexaVal "), var_name), hexa_str(" = hexa_array_new();\n")));
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_simd_preamble(HexaVal arr_name, HexaVal width) {
    HexaVal parts = hexa_array_new();
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("    // [vectorize] SIMD preamble (width="), hexa_to_string(width)), hexa_str(")\n")));
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("    int64_t __simd_len = hexa_array_len("), arr_name), hexa_str(");\n")));
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("    int64_t __simd_vec_iters = __simd_len / "), hexa_to_string(width)), hexa_str(";\n")));
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("    int64_t __simd_remainder = __simd_len % "), hexa_to_string(width)), hexa_str(";\n")));
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_simd_loop(HexaVal arr_name, HexaVal op, HexaVal scalar_expr, HexaVal width) {
    HexaVal parts = hexa_array_new();
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    // [vectorize] SIMD loop: "), arr_name), hexa_str("[i] = ")), arr_name), hexa_str("[i] ")), op), hexa_str(" scalar\n")));
    parts = hexa_array_push(parts, hexa_str("    for (int64_t __vi = 0; __vi < __simd_vec_iters; __vi++) {\n"));
    HexaVal lane = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(lane); HexaVal __r=(width); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal idx = hexa_add(hexa_add(hexa_add(hexa_str("__vi * "), hexa_to_string(width)), hexa_str(" + ")), hexa_to_string(lane));
        parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("        hexa_array_set("), arr_name), hexa_str(", ")), idx), hexa_str(", hexa_int(hexa_array_get(")), arr_name), hexa_str(", ")), idx), hexa_str(").i ")), op), hexa_str(" (")), scalar_expr), hexa_str(").i));\n")));
        lane = hexa_add(lane, hexa_int(1));
    }
    parts = hexa_array_push(parts, hexa_str("    }\n"));
    parts = hexa_array_push(parts, hexa_str("    // [vectorize] scalar remainder\n"));
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("    for (int64_t __ri = __simd_vec_iters * "), hexa_to_string(width)), hexa_str("; __ri < __simd_len; __ri++) {\n")));
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("        hexa_array_set("), arr_name), hexa_str(", __ri, hexa_int(hexa_array_get(")), arr_name), hexa_str(", __ri).i ")), op), hexa_str(" (")), scalar_expr), hexa_str(").i));\n")));
    parts = hexa_array_push(parts, hexa_str("    }\n"));
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_soa_struct_decl(HexaVal name, HexaVal fields) {
    HexaVal parts = hexa_array_new();
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("// [soa] "), name), hexa_str(" — field-parallel layout\n")));
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("HexaVal "), name), hexa_str("_soa_new(HexaVal __count) {\n")));
    parts = hexa_array_push(parts, hexa_str("    HexaVal __soa = hexa_map_new();\n"));
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(fields))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal f = hexa_index_get(fields, i);
        parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_str("    __soa = hexa_map_set(__soa, \""), f), hexa_str("s\", hexa_array_new());\n")));
        i = hexa_add(i, hexa_int(1));
    }
    parts = hexa_array_push(parts, hexa_str("    return __soa;\n"));
    parts = hexa_array_push(parts, hexa_str("}\n"));
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_struct_forward(HexaVal node) {
    HexaVal name = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_417);
    HexaVal nfields = hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_418)));
    if (hexa_truthy(hexa_eq(nfields, hexa_int(0)))) {
        return hexa_add(hexa_add(hexa_str("HexaVal "), name), hexa_str("(void);"));
    }
    HexaVal params = hexa_array_new();
    HexaVal fi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(nfields); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        params = hexa_array_push(params, hexa_add(hexa_str("HexaVal "), hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_419), fi), "name", &__hexa_codegen_c2_ic_420)));
        fi = hexa_add(fi, hexa_int(1));
    }
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("HexaVal "), name), hexa_str("(")), hexa_str_join(params, hexa_str(", "))), hexa_str(");"));
    return hexa_void();
}


HexaVal gen2_struct_decl(HexaVal node) {
    HexaVal name = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_421);
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(name, hexa_str("Val"))) && hexa_truthy(hexa_eq(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_422))), hexa_int(12)))))) {
        HexaVal vs_params = hexa_array_new();
        HexaVal vs_args = hexa_array_new();
        HexaVal vi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(vi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_423)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal fname = hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_424), vi), "name", &__hexa_codegen_c2_ic_425);
            vs_params = hexa_array_push(vs_params, hexa_add(hexa_str("HexaVal "), fname));
            vs_args = hexa_array_push(vs_args, fname);
            vi = hexa_add(vi, hexa_int(1));
        }
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("HexaVal "), name), hexa_str("(")), hexa_str_join(vs_params, hexa_str(", "))), hexa_str(") {\n    return hexa_valstruct_new_v(")), hexa_str_join(vs_args, hexa_str(", "))), hexa_str(");\n}\n"));
    }
    HexaVal params = hexa_array_new();
    HexaVal keys_parts = hexa_array_new();
    HexaVal vals_parts = hexa_array_new();
    HexaVal nfields = hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_426)));
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(nfields); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal f = hexa_index_get(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_427), i);
        params = hexa_array_push(params, hexa_add(hexa_str("HexaVal "), hexa_map_get_ic(f, "name", &__hexa_codegen_c2_ic_428)));
        if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
            keys_parts = hexa_array_push(keys_parts, hexa_str(", "));
            vals_parts = hexa_array_push(vals_parts, hexa_str(", "));
        }
        keys_parts = hexa_array_push(keys_parts, hexa_add(hexa_add(hexa_str("\""), hexa_map_get_ic(f, "name", &__hexa_codegen_c2_ic_429)), hexa_str("\"")));
        vals_parts = hexa_array_push(vals_parts, hexa_map_get_ic(f, "name", &__hexa_codegen_c2_ic_430));
        i = hexa_add(i, hexa_int(1));
    }
    HexaVal p = hexa_str_join(params, hexa_str(", "));
    HexaVal p_sig = p;
    if (hexa_truthy(hexa_eq(p_sig, hexa_str("")))) {
        p_sig = hexa_str("void");
    }
    HexaVal body = hexa_str("");
    if (hexa_truthy(hexa_eq(nfields, hexa_int(0)))) {
        body = hexa_add(hexa_add(hexa_str("    return hexa_struct_pack_map(\""), name), hexa_str("\", 0, (const char* const*)0, (const HexaVal*)0);\n"));
    } else {
        HexaVal ks_line = hexa_add(hexa_add(hexa_str("    static const char* const _k[] = {"), hexa_str_join(keys_parts, hexa_str(""))), hexa_str("};\n"));
        HexaVal vs_line = hexa_add(hexa_add(hexa_str("    HexaVal _v[] = {"), hexa_str_join(vals_parts, hexa_str(""))), hexa_str("};\n"));
        HexaVal call_line = hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    return hexa_struct_pack_map(\""), name), hexa_str("\", ")), hexa_to_string(nfields)), hexa_str(", _k, _v);\n"));
        body = hexa_add(hexa_add(ks_line, vs_line), call_line);
    }
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("HexaVal "), name), hexa_str("(")), p_sig), hexa_str(") {\n")), body), hexa_str("}\n"));
    return hexa_void();
}


HexaVal gen2_struct_decl_aligned(HexaVal node) {
    HexaVal name = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_431);
    HexaVal params = hexa_array_new();
    HexaVal body_parts = hexa_array_new();
    body_parts = hexa_array_push(body_parts, hexa_str("    // @cache_line: 64B aligned\n"));
    body_parts = hexa_array_push(body_parts, hexa_str("    HexaVal __s __attribute__((aligned(64))) = hexa_map_new();\n"));
    body_parts = hexa_array_push(body_parts, hexa_add(hexa_add(hexa_str("    __s = hexa_map_set(__s, \"__type__\", hexa_str(\""), name), hexa_str("\"));\n")));
    body_parts = hexa_array_push(body_parts, hexa_str("    __s = hexa_map_set(__s, \"__cache_line__\", hexa_int(64));\n"));
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_432)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal f = hexa_index_get(hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_433), i);
        params = hexa_array_push(params, hexa_add(hexa_str("HexaVal "), hexa_map_get_ic(f, "name", &__hexa_codegen_c2_ic_434)));
        body_parts = hexa_array_push(body_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    __s = hexa_map_set(__s, \""), hexa_map_get_ic(f, "name", &__hexa_codegen_c2_ic_435)), hexa_str("\", ")), hexa_map_get_ic(f, "name", &__hexa_codegen_c2_ic_436)), hexa_str(");\n")));
        i = hexa_add(i, hexa_int(1));
    }
    HexaVal p = hexa_str_join(params, hexa_str(", "));
    if (hexa_truthy(hexa_eq(p, hexa_str("")))) {
        p = hexa_str("void");
    }
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("HexaVal "), name), hexa_str("(")), p), hexa_str(") {\n")), hexa_str_join(body_parts, hexa_str(""))), hexa_str("    return __s;\n}\n"));
    return hexa_void();
}


HexaVal gen2_branch_predict_cond(HexaVal cond_expr) {
    return hexa_add(hexa_add(hexa_str("__builtin_expect(hexa_truthy("), gen2_expr(cond_expr)), hexa_str("), 1)"));
    return hexa_void();
}


HexaVal gen2_branch_unlikely_cond(HexaVal cond_expr) {
    return hexa_add(hexa_add(hexa_str("__builtin_expect(hexa_truthy("), gen2_expr(cond_expr)), hexa_str("), 0)"));
    return hexa_void();
}


HexaVal gen2_bitfield_accessor(HexaVal struct_name, HexaVal field_name, HexaVal bit_offset) {
    HexaVal mask = hexa_str("((1ULL << 1) - 1)");
    HexaVal getter = hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("#define "), struct_name), hexa_str("_get_")), field_name), hexa_str("(v) (((v).i >> ")), hexa_to_string(bit_offset)), hexa_str(") & ")), mask), hexa_str(")\n"));
    HexaVal setter = hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("#define "), struct_name), hexa_str("_set_")), field_name), hexa_str("(v, b) ((v).i = ((v).i & ~(")), mask), hexa_str(" << ")), hexa_to_string(bit_offset)), hexa_str(")) | (((b) & ")), mask), hexa_str(") << ")), hexa_to_string(bit_offset)), hexa_str("))\n"));
    return hexa_add(getter, setter);
    return hexa_void();
}


HexaVal gen2_enum_decl(HexaVal node) {
    HexaVal name = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_437);
    HexaVal vc = hexa_int(hexa_len(hexa_map_get_ic(node, "variants", &__hexa_codegen_c2_ic_438)));
    HexaVal tag_bits = gen2_min_bits(vc);
    HexaVal parts = hexa_array_new();
    parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("// enum "), name), hexa_str(" (")), hexa_to_string(vc)), hexa_str(" variants, ")), hexa_to_string(tag_bits)), hexa_str(" tag bit(s))\n")));
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(tag_bits); HexaVal __r=(hexa_int(8)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("// @compact: tag fits in "), hexa_to_string(tag_bits)), hexa_str(" bit(s), mask=0x")), gen2_hex_mask(tag_bits)), hexa_str("\n")));
    }
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(vc); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal v = hexa_index_get(hexa_map_get_ic(node, "variants", &__hexa_codegen_c2_ic_439), i);
        parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("#define "), name), hexa_str("_")), hexa_map_get_ic(v, "name", &__hexa_codegen_c2_ic_440)), hexa_str(" hexa_int(")), hexa_to_string(i)), hexa_str(")\n")));
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_str_join(parts, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_min_bits(HexaVal count) {
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(count); HexaVal __r=(hexa_int(1)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) <= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i <= __r.i); })))) {
        return hexa_int(1);
    }
    HexaVal bits = hexa_int(0);
    HexaVal v = hexa_sub(count, hexa_int(1));
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(v); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
        bits = hexa_add(bits, hexa_int(1));
        v = hexa_div(v, hexa_int(2));
    }
    return bits;
    return hexa_void();
}


HexaVal gen2_hex_mask(HexaVal bits) {
    if (hexa_truthy(hexa_eq(bits, hexa_int(1)))) {
        return hexa_str("01");
    }
    if (hexa_truthy(hexa_eq(bits, hexa_int(2)))) {
        return hexa_str("03");
    }
    if (hexa_truthy(hexa_eq(bits, hexa_int(3)))) {
        return hexa_str("07");
    }
    if (hexa_truthy(hexa_eq(bits, hexa_int(4)))) {
        return hexa_str("0f");
    }
    if (hexa_truthy(hexa_eq(bits, hexa_int(5)))) {
        return hexa_str("1f");
    }
    if (hexa_truthy(hexa_eq(bits, hexa_int(6)))) {
        return hexa_str("3f");
    }
    if (hexa_truthy(hexa_eq(bits, hexa_int(7)))) {
        return hexa_str("7f");
    }
    return hexa_str("ff");
    return hexa_void();
}


HexaVal gen2_match_stmt(HexaVal node, HexaVal depth) {
    HexaVal pad = gen2_indent(depth);
    HexaVal scrutinee = gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_441));
    HexaVal chunks = hexa_array_new();
    chunks = hexa_array_push(chunks, hexa_add(pad, hexa_str("{\n")));
    HexaVal pad2 = gen2_indent(hexa_add(depth, hexa_int(1)));
    chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(pad2, hexa_str("HexaVal __match_val = ")), scrutinee), hexa_str(";\n")));
    HexaVal ai = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ai); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "arms", &__hexa_codegen_c2_ic_442)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal arm = hexa_index_get(hexa_map_get_ic(node, "arms", &__hexa_codegen_c2_ic_443), ai);
        HexaVal pat = hexa_map_get_ic(arm, "left", &__hexa_codegen_c2_ic_444);
        HexaVal is_wildcard = hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(pat), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(pat, "kind", &__hexa_codegen_c2_ic_445), hexa_str("Wildcard"))));
        if (hexa_truthy(is_wildcard)) {
            if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ai); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
                chunks = hexa_array_push(chunks, hexa_str(" else {\n"));
            } else {
                chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("{\n")));
            }
        } else {
            HexaVal cond = gen2_match_cond(pat, hexa_str("__match_val"));
            if (hexa_truthy(hexa_eq(ai, hexa_int(0)))) {
                chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_add(pad2, hexa_str("if (")), cond), hexa_str(") {\n")));
            } else {
                chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_str(" else if ("), cond), hexa_str(") {\n")));
            }
        }
        HexaVal bi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(bi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(arm, "body", &__hexa_codegen_c2_ic_446)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            chunks = hexa_array_push(chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(arm, "body", &__hexa_codegen_c2_ic_447), bi), hexa_add(depth, hexa_int(2))));
            bi = hexa_add(bi, hexa_int(1));
        }
        chunks = hexa_array_push(chunks, hexa_add(pad2, hexa_str("}")));
        ai = hexa_add(ai, hexa_int(1));
    }
    chunks = hexa_array_push(chunks, hexa_add(hexa_add(hexa_str("\n"), pad), hexa_str("}\n")));
    return hexa_str_join(chunks, hexa_str(""));
    return hexa_void();
}


HexaVal gen2_match_cond(HexaVal pat, HexaVal scrutinee_var) {
    if (hexa_truthy(hexa_eq(hexa_type_of(pat), hexa_str("string")))) {
        return hexa_str("1");
    }
    HexaVal k = hexa_map_get_ic(pat, "kind", &__hexa_codegen_c2_ic_448);
    if (hexa_truthy(hexa_eq(k, hexa_str("Wildcard")))) {
        return hexa_str("1");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("IntLit")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_truthy(hexa_eq("), scrutinee_var), hexa_str(", hexa_int(")), hexa_map_get_ic(pat, "value", &__hexa_codegen_c2_ic_449)), hexa_str(")))"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("FloatLit")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_truthy(hexa_eq("), scrutinee_var), hexa_str(", hexa_float(")), hexa_map_get_ic(pat, "value", &__hexa_codegen_c2_ic_450)), hexa_str(")))"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StringLit")))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_truthy(hexa_eq("), scrutinee_var), hexa_str(", hexa_str(\"")), c_escape(hexa_map_get_ic(pat, "value", &__hexa_codegen_c2_ic_451))), hexa_str("\")))"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BoolLit")))) {
        if (hexa_truthy(hexa_eq(hexa_map_get_ic(pat, "value", &__hexa_codegen_c2_ic_452), hexa_str("true")))) {
            return hexa_add(hexa_add(hexa_str("hexa_truthy(hexa_eq("), scrutinee_var), hexa_str(", hexa_bool(1)))"));
        }
        return hexa_add(hexa_add(hexa_str("hexa_truthy(hexa_eq("), scrutinee_var), hexa_str(", hexa_bool(0)))"));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("EnumPath")))) {
        HexaVal enum_const = hexa_add(hexa_add(hexa_map_get_ic(pat, "name", &__hexa_codegen_c2_ic_453), hexa_str("_")), hexa_map_get_ic(pat, "value", &__hexa_codegen_c2_ic_454));
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_truthy(hexa_eq("), scrutinee_var), hexa_str(", ")), enum_const), hexa_str("))"));
    }
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_truthy(hexa_eq("), scrutinee_var), hexa_str(", ")), gen2_expr(pat)), hexa_str("))"));
    return hexa_void();
}


HexaVal gen2_match_expr(HexaVal node) {
    HexaVal scrutinee = gen2_expr(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_455));
    HexaVal arms = hexa_map_get_ic(node, "arms", &__hexa_codegen_c2_ic_456);
    return gen2_match_ternary(arms, scrutinee, hexa_int(0));
    return hexa_void();
}


HexaVal gen2_match_ternary(HexaVal arms, HexaVal scrutinee_c, HexaVal idx) {
    HexaVal cond = hexa_void();
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(idx); HexaVal __r=(hexa_int(hexa_len(arms))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })))) {
        return hexa_str("hexa_void()");
    }
    HexaVal arm = hexa_index_get(arms, idx);
    HexaVal pat = hexa_map_get_ic(arm, "left", &__hexa_codegen_c2_ic_457);
    HexaVal is_wildcard = hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(pat), hexa_str("string"))))) && hexa_truthy(hexa_eq(hexa_map_get_ic(pat, "kind", &__hexa_codegen_c2_ic_458), hexa_str("Wildcard"))));
    HexaVal val = gen2_arm_value(hexa_map_get_ic(arm, "body", &__hexa_codegen_c2_ic_459));
    if (hexa_truthy(hexa_bool(hexa_truthy(is_wildcard) || hexa_truthy(hexa_eq(idx, hexa_sub(hexa_int(hexa_len(arms)), hexa_int(1))))))) {
        if (hexa_truthy(is_wildcard)) {
            return val;
        }
        cond = gen2_match_cond(pat, scrutinee_c);
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("("), cond), hexa_str(" ? ")), val), hexa_str(" : hexa_void())"));
    }
    cond = gen2_match_cond(pat, scrutinee_c);
    HexaVal rest = gen2_match_ternary(arms, scrutinee_c, hexa_add(idx, hexa_int(1)));
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("("), cond), hexa_str(" ? ")), val), hexa_str(" : ")), rest), hexa_str(")"));
    return hexa_void();
}


HexaVal gen2_arm_value(HexaVal body) {
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(hexa_type_of(body), hexa_str("string"))) || hexa_truthy(hexa_eq(hexa_int(hexa_len(body)), hexa_int(0)))))) {
        return hexa_str("hexa_void()");
    }
    HexaVal last = hexa_index_get(body, hexa_sub(hexa_int(hexa_len(body)), hexa_int(1)));
    if (hexa_truthy(hexa_eq(hexa_map_get_ic(last, "kind", &__hexa_codegen_c2_ic_460), hexa_str("ExprStmt")))) {
        return gen2_expr(hexa_map_get_ic(last, "left", &__hexa_codegen_c2_ic_461));
    }
    if (hexa_truthy(hexa_eq(hexa_map_get_ic(last, "kind", &__hexa_codegen_c2_ic_462), hexa_str("ReturnStmt")))) {
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(last, "left", &__hexa_codegen_c2_ic_463)), hexa_str("string")))))) {
            return gen2_expr(hexa_map_get_ic(last, "left", &__hexa_codegen_c2_ic_464));
        }
    }
    return hexa_str("hexa_void()");
    return hexa_void();
}


HexaVal _method_registry_lookup(HexaVal name) {
    HexaVal out = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(_method_registry))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal e = hexa_index_get(_method_registry, i);
        if (hexa_truthy(hexa_eq(hexa_index_get(e, hexa_int(0)), name))) {
            out = hexa_array_push(out, hexa_index_get(e, hexa_int(1)));
        }
        i = hexa_add(i, hexa_int(1));
    }
    return out;
    return hexa_void();
}


HexaVal gen2_impl_block(HexaVal node) {
    HexaVal type_n = hexa_map_get_ic(node, "target", &__hexa_codegen_c2_ic_465);
    HexaVal fwd_chunks = hexa_array_new();
    HexaVal fn_chunks = hexa_array_new();
    HexaVal methods = hexa_map_get_ic(node, "methods", &__hexa_codegen_c2_ic_466);
    HexaVal mi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(mi); HexaVal __r=(hexa_int(hexa_len(methods))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal m = hexa_index_get(methods, mi);
        HexaVal mangled = hexa_add(hexa_add(type_n, hexa_str("__")), hexa_map_get_ic(m, "name", &__hexa_codegen_c2_ic_467));
        _method_registry = hexa_array_push(_method_registry, hexa_array_push(hexa_array_push(hexa_array_new(), hexa_map_get_ic(m, "name", &__hexa_codegen_c2_ic_468)), type_n));
        HexaVal params = hexa_array_new();
        HexaVal pi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(m, "params", &__hexa_codegen_c2_ic_469)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            params = hexa_array_push(params, hexa_add(hexa_str("HexaVal "), hexa_map_get_ic(hexa_index_get(hexa_map_get_ic(m, "params", &__hexa_codegen_c2_ic_470), pi), "name", &__hexa_codegen_c2_ic_471)));
            pi = hexa_add(pi, hexa_int(1));
        }
        HexaVal p = hexa_str_join(params, hexa_str(", "));
        if (hexa_truthy(hexa_eq(p, hexa_str("")))) {
            p = hexa_str("void");
        }
        fwd_chunks = hexa_array_push(fwd_chunks, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("HexaVal "), mangled), hexa_str("(")), p), hexa_str(");\n")));
        HexaVal body_chunks = hexa_array_new();
        body_chunks = hexa_array_push(body_chunks, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("HexaVal "), mangled), hexa_str("(")), p), hexa_str(") {\n")));
        HexaVal bi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(bi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(m, "body", &__hexa_codegen_c2_ic_472)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            body_chunks = hexa_array_push(body_chunks, gen2_stmt(hexa_index_get(hexa_map_get_ic(m, "body", &__hexa_codegen_c2_ic_473), bi), hexa_int(1)));
            bi = hexa_add(bi, hexa_int(1));
        }
        body_chunks = hexa_array_push(body_chunks, hexa_str("    return hexa_void();\n}\n\n"));
        fn_chunks = hexa_array_push(fn_chunks, hexa_str_join(body_chunks, hexa_str("")));
        mi = hexa_add(mi, hexa_int(1));
    }
    return hexa_map_set(hexa_map_set(hexa_map_new(), "forward", hexa_str_join(fwd_chunks, hexa_str(""))), "fn_code", hexa_str_join(fn_chunks, hexa_str("")));
    return hexa_void();
}


HexaVal _lookup_comptime_const(HexaVal name) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(_comptime_const_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(_comptime_const_names, i), name))) {
            return hexa_index_get(_comptime_const_nodes, i);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_str("");
    return hexa_void();
}


HexaVal _make_int_lit_node(HexaVal val_str) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("IntLit")), "name", hexa_str("")), "value", val_str), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal _make_float_lit_node(HexaVal val_str) {
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("FloatLit")), "name", hexa_str("")), "value", val_str), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal _make_bool_lit_node(HexaVal b) {
    HexaVal v = (hexa_truthy(b) ? hexa_str("true") : hexa_str("false"));
    return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("BoolLit")), "name", hexa_str("")), "value", v), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
    return hexa_void();
}


HexaVal _cf_as_float(HexaVal lit) {
    if (hexa_truthy(hexa_eq(hexa_map_get_ic(lit, "kind", &__hexa_codegen_c2_ic_474), hexa_str("FloatLit")))) {
        return hexa_float(__hx_to_double(hexa_map_get_ic(lit, "value", &__hexa_codegen_c2_ic_475)));
    }
    return hexa_float(__hx_to_double(hexa_to_string(hexa_int((hexa_map_get_ic(lit, "value", &__hexa_codegen_c2_ic_476).tag==TAG_STR?atoll(hexa_map_get_ic(lit, "value", &__hexa_codegen_c2_ic_476).s):(int64_t)__hx_to_double(hexa_map_get_ic(lit, "value", &__hexa_codegen_c2_ic_476)))))));
    return hexa_void();
}


HexaVal comptime_eval(HexaVal node) {
    HexaVal op = hexa_void();
    HexaVal ll = hexa_void();
    HexaVal rr = hexa_void();
    HexaVal lf = hexa_void();
    HexaVal rf = hexa_void();
    if (hexa_truthy(hexa_eq(hexa_type_of(node), hexa_str("string")))) {
        return hexa_str("");
    }
    HexaVal k = hexa_map_get_ic(node, "kind", &__hexa_codegen_c2_ic_477);
    if (hexa_truthy(hexa_eq(k, hexa_str("IntLit")))) {
        return node;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("FloatLit")))) {
        return node;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("StringLit")))) {
        return node;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BoolLit")))) {
        return node;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Ident")))) {
        return _lookup_comptime_const(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_478));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("UnaryOp")))) {
        op = hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_479);
        HexaVal v = comptime_eval(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_480));
        if (hexa_truthy(hexa_eq(hexa_type_of(v), hexa_str("string")))) {
            return hexa_str("");
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("-")))) {
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(v, "kind", &__hexa_codegen_c2_ic_481), hexa_str("IntLit")))) {
                HexaVal i = hexa_sub(hexa_int(0), hexa_int((hexa_map_get_ic(v, "value", &__hexa_codegen_c2_ic_482).tag==TAG_STR?atoll(hexa_map_get_ic(v, "value", &__hexa_codegen_c2_ic_482).s):(int64_t)__hx_to_double(hexa_map_get_ic(v, "value", &__hexa_codegen_c2_ic_482)))));
                return _make_int_lit_node(hexa_to_string(i));
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(v, "kind", &__hexa_codegen_c2_ic_483), hexa_str("FloatLit")))) {
                HexaVal f = hexa_sub(hexa_int(0), hexa_float(__hx_to_double(hexa_map_get_ic(v, "value", &__hexa_codegen_c2_ic_484))));
                return _make_float_lit_node(hexa_to_string(f));
            }
            return hexa_str("");
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("!")))) {
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(v, "kind", &__hexa_codegen_c2_ic_485), hexa_str("BoolLit")))) {
                return _make_bool_lit_node(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(v, "value", &__hexa_codegen_c2_ic_486), hexa_str("true")))));
            }
            return hexa_str("");
        }
        return hexa_str("");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("BinOp")))) {
        op = hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_487);
        if (hexa_truthy(hexa_eq(op, hexa_str("&&")))) {
            ll = comptime_eval(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_488));
            if (hexa_truthy(hexa_eq(hexa_type_of(ll), hexa_str("string")))) {
                return hexa_str("");
            }
            if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(ll, "kind", &__hexa_codegen_c2_ic_489), hexa_str("BoolLit")))))) {
                return hexa_str("");
            }
            if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(ll, "value", &__hexa_codegen_c2_ic_490), hexa_str("true")))))) {
                return _make_bool_lit_node(hexa_bool(0));
            }
            rr = comptime_eval(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_491));
            if (hexa_truthy(hexa_eq(hexa_type_of(rr), hexa_str("string")))) {
                return hexa_str("");
            }
            if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(rr, "kind", &__hexa_codegen_c2_ic_492), hexa_str("BoolLit")))))) {
                return hexa_str("");
            }
            return _make_bool_lit_node(hexa_eq(hexa_map_get_ic(rr, "value", &__hexa_codegen_c2_ic_493), hexa_str("true")));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("||")))) {
            ll = comptime_eval(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_494));
            if (hexa_truthy(hexa_eq(hexa_type_of(ll), hexa_str("string")))) {
                return hexa_str("");
            }
            if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(ll, "kind", &__hexa_codegen_c2_ic_495), hexa_str("BoolLit")))))) {
                return hexa_str("");
            }
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(ll, "value", &__hexa_codegen_c2_ic_496), hexa_str("true")))) {
                return _make_bool_lit_node(hexa_bool(1));
            }
            rr = comptime_eval(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_497));
            if (hexa_truthy(hexa_eq(hexa_type_of(rr), hexa_str("string")))) {
                return hexa_str("");
            }
            if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(rr, "kind", &__hexa_codegen_c2_ic_498), hexa_str("BoolLit")))))) {
                return hexa_str("");
            }
            return _make_bool_lit_node(hexa_eq(hexa_map_get_ic(rr, "value", &__hexa_codegen_c2_ic_499), hexa_str("true")));
        }
        HexaVal l = comptime_eval(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_500));
        if (hexa_truthy(hexa_eq(hexa_type_of(l), hexa_str("string")))) {
            return hexa_str("");
        }
        HexaVal r = comptime_eval(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_501));
        if (hexa_truthy(hexa_eq(hexa_type_of(r), hexa_str("string")))) {
            return hexa_str("");
        }
        HexaVal lk = hexa_map_get_ic(l, "kind", &__hexa_codegen_c2_ic_502);
        HexaVal rk = hexa_map_get_ic(r, "kind", &__hexa_codegen_c2_ic_503);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(op, hexa_str("=="))) || hexa_truthy(hexa_eq(op, hexa_str("!="))))) || hexa_truthy(hexa_eq(op, hexa_str("<"))))) || hexa_truthy(hexa_eq(op, hexa_str(">"))))) || hexa_truthy(hexa_eq(op, hexa_str("<="))))) || hexa_truthy(hexa_eq(op, hexa_str(">=")))))) {
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(lk, hexa_str("StringLit"))) && hexa_truthy(hexa_eq(rk, hexa_str("StringLit")))))) {
                if (hexa_truthy(hexa_eq(op, hexa_str("==")))) {
                    return _make_bool_lit_node(hexa_eq(hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_504), hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_505)));
                }
                if (hexa_truthy(hexa_eq(op, hexa_str("!=")))) {
                    return _make_bool_lit_node(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_506), hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_507)))));
                }
                return hexa_str("");
            }
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(lk, hexa_str("BoolLit"))) && hexa_truthy(hexa_eq(rk, hexa_str("BoolLit")))))) {
                if (hexa_truthy(hexa_eq(op, hexa_str("==")))) {
                    return _make_bool_lit_node(hexa_eq(hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_508), hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_509)));
                }
                if (hexa_truthy(hexa_eq(op, hexa_str("!=")))) {
                    return _make_bool_lit_node(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_510), hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_511)))));
                }
                return hexa_str("");
            }
            HexaVal l_num = hexa_bool(hexa_truthy(hexa_eq(lk, hexa_str("IntLit"))) || hexa_truthy(hexa_eq(lk, hexa_str("FloatLit"))));
            HexaVal r_num = hexa_bool(hexa_truthy(hexa_eq(rk, hexa_str("IntLit"))) || hexa_truthy(hexa_eq(rk, hexa_str("FloatLit"))));
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(l_num))) || hexa_truthy(hexa_bool(!hexa_truthy(r_num)))))) {
                return hexa_str("");
            }
            HexaVal mixed = hexa_bool(hexa_truthy(hexa_eq(lk, hexa_str("FloatLit"))) || hexa_truthy(hexa_eq(rk, hexa_str("FloatLit"))));
            if (hexa_truthy(mixed)) {
                lf = _cf_as_float(l);
                rf = _cf_as_float(r);
                if (hexa_truthy(hexa_eq(op, hexa_str("==")))) {
                    return _make_bool_lit_node(hexa_eq(lf, rf));
                }
                if (hexa_truthy(hexa_eq(op, hexa_str("!=")))) {
                    return _make_bool_lit_node(hexa_bool(!hexa_truthy(hexa_eq(lf, rf))));
                }
                if (hexa_truthy(hexa_eq(op, hexa_str("<")))) {
                    return _make_bool_lit_node(hexa_bool(__extension__ ({ HexaVal __l=(lf); HexaVal __r=(rf); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })));
                }
                if (hexa_truthy(hexa_eq(op, hexa_str(">")))) {
                    return _make_bool_lit_node(hexa_bool(__extension__ ({ HexaVal __l=(lf); HexaVal __r=(rf); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })));
                }
                if (hexa_truthy(hexa_eq(op, hexa_str("<=")))) {
                    return _make_bool_lit_node(hexa_bool(__extension__ ({ HexaVal __l=(lf); HexaVal __r=(rf); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) <= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i <= __r.i); })));
                }
                if (hexa_truthy(hexa_eq(op, hexa_str(">=")))) {
                    return _make_bool_lit_node(hexa_bool(__extension__ ({ HexaVal __l=(lf); HexaVal __r=(rf); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })));
                }
                return hexa_str("");
            }
            HexaVal li_c = hexa_int((hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_512).tag==TAG_STR?atoll(hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_512).s):(int64_t)__hx_to_double(hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_512))));
            HexaVal ri_c = hexa_int((hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_513).tag==TAG_STR?atoll(hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_513).s):(int64_t)__hx_to_double(hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_513))));
            if (hexa_truthy(hexa_eq(op, hexa_str("==")))) {
                return _make_bool_lit_node(hexa_eq(li_c, ri_c));
            }
            if (hexa_truthy(hexa_eq(op, hexa_str("!=")))) {
                return _make_bool_lit_node(hexa_bool(!hexa_truthy(hexa_eq(li_c, ri_c))));
            }
            if (hexa_truthy(hexa_eq(op, hexa_str("<")))) {
                return _make_bool_lit_node(hexa_bool(__extension__ ({ HexaVal __l=(li_c); HexaVal __r=(ri_c); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })));
            }
            if (hexa_truthy(hexa_eq(op, hexa_str(">")))) {
                return _make_bool_lit_node(hexa_bool(__extension__ ({ HexaVal __l=(li_c); HexaVal __r=(ri_c); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })));
            }
            if (hexa_truthy(hexa_eq(op, hexa_str("<=")))) {
                return _make_bool_lit_node(hexa_bool(__extension__ ({ HexaVal __l=(li_c); HexaVal __r=(ri_c); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) <= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i <= __r.i); })));
            }
            if (hexa_truthy(hexa_eq(op, hexa_str(">=")))) {
                return _make_bool_lit_node(hexa_bool(__extension__ ({ HexaVal __l=(li_c); HexaVal __r=(ri_c); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) >= (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i >= __r.i); })));
            }
            return hexa_str("");
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(op, hexa_str("+"))) && hexa_truthy(hexa_eq(lk, hexa_str("StringLit"))))) && hexa_truthy(hexa_eq(rk, hexa_str("StringLit")))))) {
            return hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_set(hexa_map_new(), "kind", hexa_str("StringLit")), "name", hexa_str("")), "value", hexa_add(hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_514), hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_515))), "op", hexa_str("")), "left", hexa_str("")), "right", hexa_str("")), "cond", hexa_str("")), "then_body", hexa_str("")), "else_body", hexa_str("")), "params", hexa_str("")), "body", hexa_str("")), "args", hexa_str("")), "fields", hexa_str("")), "items", hexa_str("")), "variants", hexa_str("")), "arms", hexa_str("")), "iter_expr", hexa_str("")), "ret_type", hexa_str("")), "target", hexa_str("")), "trait_name", hexa_str("")), "methods", hexa_str(""));
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(lk, hexa_str("IntLit"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(lk, hexa_str("FloatLit")))))))) {
            return hexa_str("");
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(rk, hexa_str("IntLit"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(rk, hexa_str("FloatLit")))))))) {
            return hexa_str("");
        }
        HexaVal is_float = hexa_bool(hexa_truthy(hexa_eq(lk, hexa_str("FloatLit"))) || hexa_truthy(hexa_eq(rk, hexa_str("FloatLit"))));
        if (hexa_truthy(is_float)) {
            lf = _cf_as_float(l);
            rf = _cf_as_float(r);
            if (hexa_truthy(hexa_eq(op, hexa_str("+")))) {
                return _make_float_lit_node(hexa_to_string(hexa_add(lf, rf)));
            }
            if (hexa_truthy(hexa_eq(op, hexa_str("-")))) {
                return _make_float_lit_node(hexa_to_string(hexa_sub(lf, rf)));
            }
            if (hexa_truthy(hexa_eq(op, hexa_str("*")))) {
                return _make_float_lit_node(hexa_to_string(hexa_mul(lf, rf)));
            }
            if (hexa_truthy(hexa_eq(op, hexa_str("/")))) {
                if (hexa_truthy(hexa_eq(rf, hexa_float(0.0)))) {
                    return hexa_str("");
                }
                return _make_float_lit_node(hexa_to_string(hexa_div(lf, rf)));
            }
            return hexa_str("");
        }
        HexaVal li = hexa_int((hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_516).tag==TAG_STR?atoll(hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_516).s):(int64_t)__hx_to_double(hexa_map_get_ic(l, "value", &__hexa_codegen_c2_ic_516))));
        HexaVal ri = hexa_int((hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_517).tag==TAG_STR?atoll(hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_517).s):(int64_t)__hx_to_double(hexa_map_get_ic(r, "value", &__hexa_codegen_c2_ic_517))));
        if (hexa_truthy(hexa_eq(op, hexa_str("+")))) {
            return _make_int_lit_node(hexa_to_string(hexa_add(li, ri)));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("-")))) {
            return _make_int_lit_node(hexa_to_string(hexa_sub(li, ri)));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("*")))) {
            return _make_int_lit_node(hexa_to_string(hexa_mul(li, ri)));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("/")))) {
            if (hexa_truthy(hexa_eq(ri, hexa_int(0)))) {
                return hexa_str("");
            }
            return _make_int_lit_node(hexa_to_string(hexa_div(li, ri)));
        }
        if (hexa_truthy(hexa_eq(op, hexa_str("%")))) {
            if (hexa_truthy(hexa_eq(ri, hexa_int(0)))) {
                return hexa_str("");
            }
            return _make_int_lit_node(hexa_to_string(hexa_mod(li, ri)));
        }
        return hexa_str("");
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("IfExpr")))) {
        HexaVal c = comptime_eval(hexa_map_get_ic(node, "cond", &__hexa_codegen_c2_ic_518));
        if (hexa_truthy(hexa_eq(hexa_type_of(c), hexa_str("string")))) {
            return hexa_str("");
        }
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(c, "kind", &__hexa_codegen_c2_ic_519), hexa_str("BoolLit")))))) {
            return hexa_str("");
        }
        HexaVal pick_true = hexa_eq(hexa_map_get_ic(c, "value", &__hexa_codegen_c2_ic_520), hexa_str("true"));
        HexaVal body = (hexa_truthy(pick_true) ? hexa_map_get_ic(node, "then_body", &__hexa_codegen_c2_ic_521) : hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_522));
        if (hexa_truthy(hexa_eq(hexa_type_of(body), hexa_str("string")))) {
            return hexa_str("");
        }
        if (hexa_truthy(hexa_eq(hexa_int(hexa_len(body)), hexa_int(0)))) {
            return hexa_str("");
        }
        HexaVal last = hexa_index_get(body, hexa_sub(hexa_int(hexa_len(body)), hexa_int(1)));
        if (hexa_truthy(hexa_eq(hexa_type_of(last), hexa_str("string")))) {
            return hexa_str("");
        }
        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_map_get_ic(last, "kind", &__hexa_codegen_c2_ic_523), hexa_str("ExprStmt")))))) {
            return hexa_str("");
        }
        if (hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(last, "left", &__hexa_codegen_c2_ic_524)), hexa_str("string")))) {
            return hexa_str("");
        }
        return comptime_eval(hexa_map_get_ic(last, "left", &__hexa_codegen_c2_ic_525));
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Call")))) {
        HexaVal fname = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_526);
        if (hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_527)), hexa_str("string")))) {
            return hexa_str("");
        }
        HexaVal nargs = hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_528)));
        if (hexa_truthy(hexa_eq(nargs, hexa_int(1)))) {
            HexaVal a = comptime_eval(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_529), hexa_int(0)));
            if (hexa_truthy(hexa_eq(hexa_type_of(a), hexa_str("string")))) {
                return hexa_str("");
            }
            HexaVal ak = hexa_map_get_ic(a, "kind", &__hexa_codegen_c2_ic_530);
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(ak, hexa_str("IntLit"))))) && hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(ak, hexa_str("FloatLit")))))))) {
                return hexa_str("");
            }
            if (hexa_truthy(hexa_eq(fname, hexa_str("abs")))) {
                if (hexa_truthy(hexa_eq(ak, hexa_str("IntLit")))) {
                    HexaVal iv = hexa_int((hexa_map_get_ic(a, "value", &__hexa_codegen_c2_ic_531).tag==TAG_STR?atoll(hexa_map_get_ic(a, "value", &__hexa_codegen_c2_ic_531).s):(int64_t)__hx_to_double(hexa_map_get_ic(a, "value", &__hexa_codegen_c2_ic_531))));
                    HexaVal ar = (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(iv); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) ? hexa_sub(hexa_int(0), iv) : iv);
                    return _make_int_lit_node(hexa_to_string(ar));
                }
                HexaVal fv = hexa_float(__hx_to_double(hexa_map_get_ic(a, "value", &__hexa_codegen_c2_ic_532)));
                HexaVal fr = (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fv); HexaVal __r=(hexa_float(0.0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) ? hexa_sub(hexa_float(0.0), fv) : fv);
                return _make_float_lit_node(hexa_to_string(fr));
            }
            if (hexa_truthy(hexa_eq(fname, hexa_str("sqrt")))) {
                HexaVal fv2 = _cf_as_float(a);
                if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fv2); HexaVal __r=(hexa_float(0.0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                    return hexa_str("");
                }
                if (hexa_truthy(hexa_eq(ak, hexa_str("IntLit")))) {
                    HexaVal iv2 = hexa_int((hexa_map_get_ic(a, "value", &__hexa_codegen_c2_ic_533).tag==TAG_STR?atoll(hexa_map_get_ic(a, "value", &__hexa_codegen_c2_ic_533).s):(int64_t)__hx_to_double(hexa_map_get_ic(a, "value", &__hexa_codegen_c2_ic_533))));
                    HexaVal s = hexa_int(0);
                    while (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_mul(s, s)); HexaVal __r=(iv2); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); }))) && hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(s); HexaVal __r=(hexa_int(10000)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))))) {
                        s = hexa_add(s, hexa_int(1));
                    }
                    if (hexa_truthy(hexa_eq(hexa_mul(s, s), iv2))) {
                        return _make_float_lit_node(hexa_to_string(hexa_float(__hx_to_double(hexa_to_string(s)))));
                    }
                    return hexa_str("");
                }
                return hexa_str("");
            }
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(fname, hexa_str("floor"))) || hexa_truthy(hexa_eq(fname, hexa_str("ceil")))))) {
                if (hexa_truthy(hexa_eq(ak, hexa_str("IntLit")))) {
                    return _make_int_lit_node(hexa_map_get_ic(a, "value", &__hexa_codegen_c2_ic_534));
                }
                return hexa_str("");
            }
            return hexa_str("");
        }
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(nargs, hexa_int(2))) && hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(fname, hexa_str("min"))) || hexa_truthy(hexa_eq(fname, hexa_str("max")))))))) {
            HexaVal a1 = comptime_eval(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_535), hexa_int(0)));
            if (hexa_truthy(hexa_eq(hexa_type_of(a1), hexa_str("string")))) {
                return hexa_str("");
            }
            HexaVal a2 = comptime_eval(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_536), hexa_int(1)));
            if (hexa_truthy(hexa_eq(hexa_type_of(a2), hexa_str("string")))) {
                return hexa_str("");
            }
            HexaVal k1 = hexa_map_get_ic(a1, "kind", &__hexa_codegen_c2_ic_537);
            HexaVal k2 = hexa_map_get_ic(a2, "kind", &__hexa_codegen_c2_ic_538);
            HexaVal n1 = hexa_bool(hexa_truthy(hexa_eq(k1, hexa_str("IntLit"))) || hexa_truthy(hexa_eq(k1, hexa_str("FloatLit"))));
            HexaVal n2 = hexa_bool(hexa_truthy(hexa_eq(k2, hexa_str("IntLit"))) || hexa_truthy(hexa_eq(k2, hexa_str("FloatLit"))));
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(!hexa_truthy(n1))) || hexa_truthy(hexa_bool(!hexa_truthy(n2)))))) {
                return hexa_str("");
            }
            if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k1, hexa_str("IntLit"))) && hexa_truthy(hexa_eq(k2, hexa_str("IntLit")))))) {
                HexaVal v1 = hexa_int((hexa_map_get_ic(a1, "value", &__hexa_codegen_c2_ic_539).tag==TAG_STR?atoll(hexa_map_get_ic(a1, "value", &__hexa_codegen_c2_ic_539).s):(int64_t)__hx_to_double(hexa_map_get_ic(a1, "value", &__hexa_codegen_c2_ic_539))));
                HexaVal v2 = hexa_int((hexa_map_get_ic(a2, "value", &__hexa_codegen_c2_ic_540).tag==TAG_STR?atoll(hexa_map_get_ic(a2, "value", &__hexa_codegen_c2_ic_540).s):(int64_t)__hx_to_double(hexa_map_get_ic(a2, "value", &__hexa_codegen_c2_ic_540))));
                HexaVal pick = (hexa_truthy(hexa_eq(fname, hexa_str("min"))) ? hexa_bool(__extension__ ({ HexaVal __l=(v1); HexaVal __r=(v2); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })) : hexa_bool(__extension__ ({ HexaVal __l=(v1); HexaVal __r=(v2); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })));
                HexaVal out = (hexa_truthy(pick) ? v1 : v2);
                return _make_int_lit_node(hexa_to_string(out));
            }
            HexaVal f1 = _cf_as_float(a1);
            HexaVal f2 = _cf_as_float(a2);
            HexaVal pickf = (hexa_truthy(hexa_eq(fname, hexa_str("min"))) ? hexa_bool(__extension__ ({ HexaVal __l=(f1); HexaVal __r=(f2); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })) : hexa_bool(__extension__ ({ HexaVal __l=(f1); HexaVal __r=(f2); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })));
            HexaVal outf = (hexa_truthy(pickf) ? f1 : f2);
            return _make_float_lit_node(hexa_to_string(outf));
        }
        return hexa_str("");
    }
    return hexa_str("");
    return hexa_void();
}


HexaVal _register_comptime_const(HexaVal name, HexaVal value_node) {
    _comptime_const_names = hexa_array_push(_comptime_const_names, name);
    _comptime_const_nodes = hexa_array_push(_comptime_const_nodes, value_node);
    return hexa_void();
}


HexaVal _is_known_fn_global(HexaVal name) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(_known_fn_globals))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(_known_fn_globals, i), name))) {
            return hexa_bool(1);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal _is_known_nonlocal(HexaVal name) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(_known_nonlocal_names))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(_known_nonlocal_names, i), name))) {
            return hexa_bool(1);
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal _is_known_global(HexaVal name) {
    return _is_known_nonlocal(name);
    return hexa_void();
}


HexaVal _is_builtin_name(HexaVal name) {
    if (hexa_truthy(hexa_eq(name, hexa_str("println")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("print")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("eprintln")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("len")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("to_string")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("type_of")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("sqrt")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("floor")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("ceil")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("abs")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("round")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("ln")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("log")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("log10")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("exp")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("sin")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("cos")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("pow")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("to_float")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("to_int")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("min")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("max")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("format")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("args")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("exec")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("read_file")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("write_file")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("file_exists")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("is_alpha")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("is_digit")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("is_alphanumeric")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("true")))) {
        return hexa_bool(1);
    }
    if (hexa_truthy(hexa_eq(name, hexa_str("false")))) {
        return hexa_bool(1);
    }
    return hexa_bool(0);
    return hexa_void();
}


HexaVal _add_unique(HexaVal list, HexaVal name) {
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(list))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        if (hexa_truthy(hexa_eq(hexa_index_get(list, i), name))) {
            return list;
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_array_push(list, name);
    return hexa_void();
}


HexaVal gen2_collect_free(HexaVal node, HexaVal bound, HexaVal out) {
    HexaVal result = hexa_void();
    if (hexa_truthy(hexa_eq(hexa_type_of(node), hexa_str("string")))) {
        return out;
    }
    if (hexa_truthy(hexa_eq(hexa_type_of(node), hexa_str("array")))) {
        HexaVal local = bound;
        result = out;
        HexaVal i = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(node))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal s = hexa_index_get(node, i);
            if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(s), hexa_str("string")))))) {
                HexaVal sk = hexa_map_get_ic(s, "kind", &__hexa_codegen_c2_ic_541);
                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(sk, hexa_str("LetStmt"))) || hexa_truthy(hexa_eq(sk, hexa_str("LetMutStmt")))))) {
                    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(s, "left", &__hexa_codegen_c2_ic_542)), hexa_str("string")))))) {
                        result = gen2_collect_free(hexa_map_get_ic(s, "left", &__hexa_codegen_c2_ic_543), local, result);
                    }
                    local = hexa_array_push(local, hexa_map_get_ic(s, "name", &__hexa_codegen_c2_ic_544));
                } else {
                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(sk, hexa_str("ForStmt"))) || hexa_truthy(hexa_eq(sk, hexa_str("ForInStmt")))))) {
                        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(s, "left", &__hexa_codegen_c2_ic_545)), hexa_str("string")))))) {
                            result = gen2_collect_free(hexa_map_get_ic(s, "left", &__hexa_codegen_c2_ic_546), local, result);
                        }
                        HexaVal body_local = hexa_array_push(local, hexa_map_get_ic(s, "name", &__hexa_codegen_c2_ic_547));
                        if (hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(s, "body", &__hexa_codegen_c2_ic_548)), hexa_str("array")))) {
                            result = gen2_collect_free(hexa_map_get_ic(s, "body", &__hexa_codegen_c2_ic_549), body_local, result);
                        }
                    } else {
                        result = gen2_collect_free(s, local, result);
                    }
                }
            }
            i = hexa_add(i, hexa_int(1));
        }
        return result;
    }
    HexaVal k = hexa_map_get_ic(node, "kind", &__hexa_codegen_c2_ic_550);
    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("IntLit"))) || hexa_truthy(hexa_eq(k, hexa_str("FloatLit"))))) || hexa_truthy(hexa_eq(k, hexa_str("StringLit"))))) || hexa_truthy(hexa_eq(k, hexa_str("BoolLit"))))) || hexa_truthy(hexa_eq(k, hexa_str("CharLit"))))) || hexa_truthy(hexa_eq(k, hexa_str("Wildcard")))))) {
        return out;
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Ident")))) {
        HexaVal name = hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_551);
        if (hexa_truthy(_is_known_global(name))) {
            return out;
        }
        if (hexa_truthy(_is_builtin_name(name))) {
            return out;
        }
        HexaVal bi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(bi); HexaVal __r=(hexa_int(hexa_len(bound))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            if (hexa_truthy(hexa_eq(hexa_index_get(bound, bi), name))) {
                return out;
            }
            bi = hexa_add(bi, hexa_int(1));
        }
        return _add_unique(out, name);
    }
    if (hexa_truthy(hexa_eq(k, hexa_str("Lambda")))) {
        HexaVal inner_bound = bound;
        HexaVal pi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_552)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            inner_bound = hexa_array_push(inner_bound, hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_553), pi));
            pi = hexa_add(pi, hexa_int(1));
        }
        return gen2_collect_free(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_554), inner_bound, out);
    }
    result = out;
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_555)), hexa_str("string")))))) {
        result = gen2_collect_free(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_556), bound, result);
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_557)), hexa_str("string")))))) {
        result = gen2_collect_free(hexa_map_get_ic(node, "right", &__hexa_codegen_c2_ic_558), bound, result);
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "cond", &__hexa_codegen_c2_ic_559)), hexa_str("string")))))) {
        result = gen2_collect_free(hexa_map_get_ic(node, "cond", &__hexa_codegen_c2_ic_560), bound, result);
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "then_body", &__hexa_codegen_c2_ic_561)), hexa_str("string")))))) {
        result = gen2_collect_free(hexa_map_get_ic(node, "then_body", &__hexa_codegen_c2_ic_562), bound, result);
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_563)), hexa_str("string")))))) {
        result = gen2_collect_free(hexa_map_get_ic(node, "else_body", &__hexa_codegen_c2_ic_564), bound, result);
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_565)), hexa_str("string")))))) {
        result = gen2_collect_free(hexa_map_get_ic(node, "body", &__hexa_codegen_c2_ic_566), bound, result);
    }
    if (hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_567)), hexa_str("array")))) {
        HexaVal ai = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ai); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_568)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            result = gen2_collect_free(hexa_index_get(hexa_map_get_ic(node, "args", &__hexa_codegen_c2_ic_569), ai), bound, result);
            ai = hexa_add(ai, hexa_int(1));
        }
    }
    if (hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "items", &__hexa_codegen_c2_ic_570)), hexa_str("array")))) {
        HexaVal ii = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(ii); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "items", &__hexa_codegen_c2_ic_571)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            result = gen2_collect_free(hexa_index_get(hexa_map_get_ic(node, "items", &__hexa_codegen_c2_ic_572), ii), bound, result);
            ii = hexa_add(ii, hexa_int(1));
        }
    }
    if (hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(node, "arms", &__hexa_codegen_c2_ic_573)), hexa_str("array")))) {
        HexaVal mi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(mi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "arms", &__hexa_codegen_c2_ic_574)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            HexaVal arm = hexa_index_get(hexa_map_get_ic(node, "arms", &__hexa_codegen_c2_ic_575), mi);
            if (hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(arm, "body", &__hexa_codegen_c2_ic_576)), hexa_str("array")))) {
                result = gen2_collect_free(hexa_map_get_ic(arm, "body", &__hexa_codegen_c2_ic_577), bound, result);
            }
            mi = hexa_add(mi, hexa_int(1));
        }
    }
    return result;
    return hexa_void();
}


HexaVal gen2_lambda_expr(HexaVal node) {
    HexaVal fi = hexa_void();
    HexaVal id = _lambda_counter;
    _lambda_counter = hexa_add(_lambda_counter, hexa_int(1));
    HexaVal fn_name = hexa_add(hexa_str("__hexa_lambda_"), hexa_to_string(id));
    HexaVal bound = hexa_array_new();
    HexaVal pi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_578)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        bound = hexa_array_push(bound, hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_579), pi));
        pi = hexa_add(pi, hexa_int(1));
    }
    HexaVal free_vars = gen2_collect_free(hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_580), bound, hexa_array_new());
    HexaVal arity = hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_581)));
    HexaVal params = hexa_array_new();
    params = hexa_array_push(params, hexa_str("HexaVal __env"));
    pi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(pi); HexaVal __r=(hexa_int(hexa_len(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_582)))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        params = hexa_array_push(params, hexa_add(hexa_str("HexaVal "), hexa_index_get(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_583), pi)));
        pi = hexa_add(pi, hexa_int(1));
    }
    HexaVal p = hexa_str_join(params, hexa_str(", "));
    if (hexa_truthy(hexa_eq(p, hexa_str("")))) {
        p = hexa_str("void");
    }
    HexaVal body_parts = hexa_array_new();
    if (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(hexa_int(hexa_len(free_vars))); HexaVal __r=(hexa_int(0)); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) > (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i > __r.i); })))) {
        fi = hexa_int(0);
        while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(hexa_int(hexa_len(free_vars))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
            body_parts = hexa_array_push(body_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    HexaVal "), hexa_index_get(free_vars, fi)), hexa_str(" = hexa_array_get(__env, ")), hexa_to_string(fi)), hexa_str(");\n")));
            fi = hexa_add(fi, hexa_int(1));
        }
    }
    HexaVal lbody = hexa_map_get_ic(node, "left", &__hexa_codegen_c2_ic_584);
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(lbody), hexa_str("string")))))) {
        if (hexa_truthy(hexa_eq(hexa_type_of(lbody), hexa_str("array")))) {
            HexaVal bi = hexa_int(0);
            while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(bi); HexaVal __r=(hexa_int(hexa_len(lbody))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
                body_parts = hexa_array_push(body_parts, gen2_stmt(hexa_index_get(lbody, bi), hexa_int(1)));
                bi = hexa_add(bi, hexa_int(1));
            }
        } else {
            body_parts = hexa_array_push(body_parts, hexa_add(hexa_add(hexa_str("    return "), gen2_expr(lbody)), hexa_str(";\n")));
        }
    }
    HexaVal fn_def = hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("HexaVal "), fn_name), hexa_str("(")), p), hexa_str(") {\n")), hexa_str_join(body_parts, hexa_str(""))), hexa_str("    return hexa_void();\n}\n\n"));
    _lambda_def_parts = hexa_array_push(_lambda_def_parts, fn_def);
    if (hexa_truthy(hexa_eq(hexa_int(hexa_len(free_vars)), hexa_int(0)))) {
        return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_closure_new((void*)&"), fn_name), hexa_str(", ")), hexa_to_string(arity)), hexa_str(", hexa_array_new())"));
    }
    HexaVal env_expr = hexa_str("hexa_array_new()");
    fi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(fi); HexaVal __r=(hexa_int(hexa_len(free_vars))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        env_expr = hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_array_push("), env_expr), hexa_str(", ")), hexa_index_get(free_vars, fi)), hexa_str(")"));
        fi = hexa_add(fi, hexa_int(1));
    }
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("hexa_closure_new((void*)&"), fn_name), hexa_str(", ")), hexa_to_string(arity)), hexa_str(", ")), env_expr), hexa_str(")"));
    return hexa_void();
}


HexaVal codegen_c2_full(HexaVal ast) {
    _lambda_counter = hexa_int(0);
    _lambda_def_parts = hexa_array_new();
    _method_registry = hexa_array_new();
    _known_fn_globals = hexa_array_new();
    _known_nonlocal_names = hexa_array_new();
    _ic_counter = hexa_int(0);
    _ic_def_parts = hexa_array_new();
    _comptime_const_names = hexa_array_new();
    _comptime_const_nodes = hexa_array_new();
    HexaVal gi = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(gi); HexaVal __r=(hexa_int(hexa_len(ast))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal gk = hexa_map_get_ic(hexa_index_get(ast, gi), "kind", &__hexa_codegen_c2_ic_585);
        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(gk, hexa_str("FnDecl"))) || hexa_truthy(hexa_eq(gk, hexa_str("ExternFnDecl"))))) || hexa_truthy(hexa_eq(gk, hexa_str("PureFnDecl"))))) || hexa_truthy(hexa_eq(gk, hexa_str("OptimizeFnStmt")))))) {
            _known_fn_globals = hexa_array_push(_known_fn_globals, hexa_map_get_ic(hexa_index_get(ast, gi), "name", &__hexa_codegen_c2_ic_586));
            _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, gi), "name", &__hexa_codegen_c2_ic_587));
        } else {
            if (hexa_truthy(hexa_eq(gk, hexa_str("StructDecl")))) {
                _known_fn_globals = hexa_array_push(_known_fn_globals, hexa_map_get_ic(hexa_index_get(ast, gi), "name", &__hexa_codegen_c2_ic_588));
                _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, gi), "name", &__hexa_codegen_c2_ic_589));
            } else {
                if (hexa_truthy(hexa_eq(gk, hexa_str("EnumDecl")))) {
                    _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, gi), "name", &__hexa_codegen_c2_ic_590));
                } else {
                    if (hexa_truthy(hexa_eq(gk, hexa_str("ComptimeConst")))) {
                        _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, gi), "name", &__hexa_codegen_c2_ic_591));
                    } else {
                        if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(gk, hexa_str("LetMutStmt"))) || hexa_truthy(hexa_eq(gk, hexa_str("LetStmt")))))) {
                            _known_nonlocal_names = hexa_array_push(_known_nonlocal_names, hexa_map_get_ic(hexa_index_get(ast, gi), "name", &__hexa_codegen_c2_ic_592));
                        }
                    }
                }
            }
        }
        gi = hexa_add(gi, hexa_int(1));
    }
    HexaVal fwd_parts = hexa_array_new();
    HexaVal global_parts = hexa_array_new();
    HexaVal fn_parts = hexa_array_new();
    HexaVal main_parts = hexa_array_new();
    HexaVal has_user_main = hexa_bool(0);
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(ast))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal k = hexa_map_get_ic(hexa_index_get(ast, i), "kind", &__hexa_codegen_c2_ic_593);
        if (hexa_truthy(hexa_eq(k, hexa_str("FnDecl")))) {
            if (hexa_truthy(hexa_eq(hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_594), hexa_str("main")))) {
                has_user_main = hexa_bool(1);
            }
            fwd_parts = hexa_array_push(fwd_parts, hexa_add(gen2_fn_forward(hexa_index_get(ast, i)), hexa_str("\n")));
            fn_parts = hexa_array_push(fn_parts, hexa_add(gen2_fn_decl(hexa_index_get(ast, i)), hexa_str("\n\n")));
        } else {
            if (hexa_truthy(hexa_eq(k, hexa_str("ExternFnDecl")))) {
                HexaVal ew = gen2_extern_wrapper(hexa_index_get(ast, i));
                global_parts = hexa_array_push(global_parts, hexa_map_get_ic(ew, "global", &__hexa_codegen_c2_ic_595));
                fwd_parts = hexa_array_push(fwd_parts, hexa_add(hexa_map_get_ic(ew, "forward", &__hexa_codegen_c2_ic_596), hexa_str("\n")));
                fn_parts = hexa_array_push(fn_parts, hexa_add(hexa_map_get_ic(ew, "fn_code", &__hexa_codegen_c2_ic_597), hexa_str("\n\n")));
                main_parts = hexa_array_push(main_parts, hexa_map_get_ic(ew, "init", &__hexa_codegen_c2_ic_598));
            } else {
                if (hexa_truthy(hexa_eq(k, hexa_str("StructDecl")))) {
                    fwd_parts = hexa_array_push(fwd_parts, hexa_add(gen2_struct_forward(hexa_index_get(ast, i)), hexa_str("\n")));
                    fn_parts = hexa_array_push(fn_parts, hexa_add(gen2_struct_decl(hexa_index_get(ast, i)), hexa_str("\n\n")));
                } else {
                    if (hexa_truthy(hexa_eq(k, hexa_str("EnumDecl")))) {
                        fn_parts = hexa_array_push(fn_parts, hexa_add(gen2_enum_decl(hexa_index_get(ast, i)), hexa_str("\n")));
                    } else {
                        if (hexa_truthy(hexa_eq(k, hexa_str("ImplBlock")))) {
                            HexaVal ib = gen2_impl_block(hexa_index_get(ast, i));
                            fwd_parts = hexa_array_push(fwd_parts, hexa_map_get_ic(ib, "forward", &__hexa_codegen_c2_ic_599));
                            fn_parts = hexa_array_push(fn_parts, hexa_map_get_ic(ib, "fn_code", &__hexa_codegen_c2_ic_600));
                        } else {
                            if (hexa_truthy(hexa_eq(k, hexa_str("PureFnDecl")))) {
                                fwd_parts = hexa_array_push(fwd_parts, hexa_add(gen2_fn_forward(hexa_index_get(ast, i)), hexa_str("\n")));
                                fn_parts = hexa_array_push(fn_parts, hexa_add(gen2_fn_decl(hexa_index_get(ast, i)), hexa_str("\n\n")));
                            } else {
                                if (hexa_truthy(hexa_eq(k, hexa_str("ComptimeConst")))) {
                                    HexaVal _cc_folded2 = comptime_eval(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_601));
                                    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(_cc_folded2), hexa_str("string")))))) {
                                        _register_comptime_const(hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_602), _cc_folded2);
                                    } else {
                                        global_parts = hexa_array_push(global_parts, hexa_add(hexa_add(hexa_str("HexaVal "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_603)), hexa_str(";\n")));
                                        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_604)), hexa_str("string")))))) {
                                            main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_605)), hexa_str(" = ")), gen2_expr(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_606))), hexa_str(";\n")));
                                        } else {
                                            main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_str("    "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_607)), hexa_str(" = hexa_void();\n")));
                                        }
                                    }
                                } else {
                                    if (hexa_truthy(hexa_eq(k, hexa_str("OptimizeFnStmt")))) {
                                    } else {
                                        if (hexa_truthy(hexa_eq(k, hexa_str("TraitDecl")))) {
                                        } else {
                                            if (hexa_truthy(hexa_eq(k, hexa_str("InvariantDecl")))) {
                                            } else {
                                                if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("ImportStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("UseStmt")))))) {
                                                    (hexa_eprint_val(hexa_add(hexa_str("[codegen_c2] WARNING: import/use not fully resolved: "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_608))), fprintf(stderr, "\n"), hexa_void());
                                                    main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_str("    /* import: "), hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_609)), hexa_str(" */\n")));
                                                } else {
                                                    if (hexa_truthy(hexa_bool(hexa_truthy(hexa_eq(k, hexa_str("LetMutStmt"))) || hexa_truthy(hexa_eq(k, hexa_str("LetStmt")))))) {
                                                        HexaVal _user_name2 = _hexa_mangle_ident(hexa_map_get_ic(hexa_index_get(ast, i), "name", &__hexa_codegen_c2_ic_610));
                                                        HexaVal _tls_val2 = hexa_map_get_ic(hexa_index_get(ast, i), "value", &__hexa_codegen_c2_ic_611);
                                                        HexaVal _is_tls2 = hexa_bool(0);
                                                        if (hexa_truthy(hexa_eq(hexa_type_of(_tls_val2), hexa_str("string")))) {
                                                            if (hexa_truthy(hexa_eq(_tls_val2, hexa_str("thread_local")))) {
                                                                _is_tls2 = hexa_bool(1);
                                                            }
                                                        }
                                                        if (hexa_truthy(_is_tls2)) {
                                                            global_parts = hexa_array_push(global_parts, hexa_add(hexa_add(hexa_str("_Thread_local HexaVal "), _user_name2), hexa_str(";\n")));
                                                        } else {
                                                            global_parts = hexa_array_push(global_parts, hexa_add(hexa_add(hexa_str("HexaVal "), _user_name2), hexa_str(";\n")));
                                                        }
                                                        if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(hexa_type_of(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_612)), hexa_str("string")))))) {
                                                            main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("    "), _user_name2), hexa_str(" = ")), gen2_expr(hexa_map_get_ic(hexa_index_get(ast, i), "left", &__hexa_codegen_c2_ic_613))), hexa_str(";\n")));
                                                        } else {
                                                            main_parts = hexa_array_push(main_parts, hexa_add(hexa_add(hexa_str("    "), _user_name2), hexa_str(" = hexa_void();\n")));
                                                        }
                                                    } else {
                                                        main_parts = hexa_array_push(main_parts, gen2_stmt(hexa_index_get(ast, i), hexa_int(1)));
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        i = hexa_add(i, hexa_int(1));
    }
    HexaVal out_parts = hexa_array_new();
    out_parts = hexa_array_push(out_parts, hexa_str("// Generated by HEXA self-host compiler\n"));
    out_parts = hexa_array_push(out_parts, hexa_str("#include \"runtime.c\"\n\n"));
    out_parts = hexa_array_push(out_parts, hexa_str_join(fwd_parts, hexa_str("")));
    out_parts = hexa_array_push(out_parts, hexa_str("\n"));
    out_parts = hexa_array_push(out_parts, hexa_str_join(global_parts, hexa_str("")));
    out_parts = hexa_array_push(out_parts, hexa_str("\n"));
    out_parts = hexa_array_push(out_parts, hexa_str_join(_ic_def_parts, hexa_str("")));
    out_parts = hexa_array_push(out_parts, hexa_str("\n"));
    out_parts = hexa_array_push(out_parts, hexa_str_join(_lambda_def_parts, hexa_str("")));
    out_parts = hexa_array_push(out_parts, hexa_str_join(fn_parts, hexa_str("")));
    out_parts = hexa_array_push(out_parts, hexa_str("int main(int argc, char** argv) {\n"));
    out_parts = hexa_array_push(out_parts, hexa_str("    hexa_set_args(argc, argv);\n"));
    out_parts = hexa_array_push(out_parts, hexa_str_join(main_parts, hexa_str("")));
    if (hexa_truthy(has_user_main)) {
        out_parts = hexa_array_push(out_parts, hexa_str("    u_main();\n"));
    }
    out_parts = hexa_array_push(out_parts, hexa_str("    return 0;\n}\n"));
    return hexa_str_join(out_parts, hexa_str(""));
    return hexa_void();
}


HexaVal _hxi_params_str(HexaVal params) {
    if (hexa_truthy(hexa_eq(hexa_type_of(params), hexa_str("string")))) {
        return hexa_str("");
    }
    HexaVal parts = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(params))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal p = hexa_index_get(params, i);
        HexaVal vt = hexa_to_string(hexa_map_get_ic(p, "value", &__hexa_codegen_c2_ic_614));
        HexaVal t = (hexa_truthy(hexa_eq(vt, hexa_str(""))) ? hexa_str("_") : vt);
        parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_to_string(hexa_map_get_ic(p, "name", &__hexa_codegen_c2_ic_615)), hexa_str(":")), t));
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_str_join(parts, hexa_str(","));
    return hexa_void();
}


HexaVal _hxi_fn_line(HexaVal node) {
    HexaVal ret = hexa_to_string(hexa_map_get_ic(node, "ret_type", &__hexa_codegen_c2_ic_616));
    HexaVal ret_s = (hexa_truthy(hexa_eq(ret, hexa_str(""))) ? hexa_str("void") : ret);
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("fn "), hexa_to_string(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_617))), hexa_str("(")), _hxi_params_str(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_618))), hexa_str(")->")), ret_s);
    return hexa_void();
}


HexaVal _hxi_struct_line(HexaVal node) {
    HexaVal fields = hexa_map_get_ic(node, "fields", &__hexa_codegen_c2_ic_619);
    if (hexa_truthy(hexa_eq(hexa_type_of(fields), hexa_str("string")))) {
        return hexa_add(hexa_add(hexa_str("struct "), hexa_to_string(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_620))), hexa_str("()"));
    }
    HexaVal parts = hexa_array_new();
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(fields))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal f = hexa_index_get(fields, i);
        HexaVal vt = hexa_to_string(hexa_map_get_ic(f, "value", &__hexa_codegen_c2_ic_621));
        HexaVal t = (hexa_truthy(hexa_eq(vt, hexa_str(""))) ? hexa_str("_") : vt);
        parts = hexa_array_push(parts, hexa_add(hexa_add(hexa_to_string(hexa_map_get_ic(f, "name", &__hexa_codegen_c2_ic_622)), hexa_str(":")), t));
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("struct "), hexa_to_string(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_623))), hexa_str("(")), hexa_str_join(parts, hexa_str(","))), hexa_str(")"));
    return hexa_void();
}


HexaVal _hxi_extern_line(HexaVal node) {
    HexaVal ret = hexa_to_string(hexa_map_get_ic(node, "ret_type", &__hexa_codegen_c2_ic_624));
    HexaVal ret_s = (hexa_truthy(hexa_eq(ret, hexa_str(""))) ? hexa_str("void") : ret);
    HexaVal sym = hexa_to_string(hexa_map_get_ic(node, "value", &__hexa_codegen_c2_ic_625));
    HexaVal link = hexa_to_string(hexa_map_get_ic(node, "op", &__hexa_codegen_c2_ic_626));
    HexaVal line = hexa_add(hexa_add(hexa_add(hexa_add(hexa_add(hexa_str("extern "), hexa_to_string(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_627))), hexa_str("(")), _hxi_params_str(hexa_map_get_ic(node, "params", &__hexa_codegen_c2_ic_628))), hexa_str(")->")), ret_s);
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(sym, hexa_str("")))))) {
        line = hexa_add(hexa_add(line, hexa_str(" @symbol=")), sym);
    }
    if (hexa_truthy(hexa_bool(!hexa_truthy(hexa_eq(link, hexa_str("")))))) {
        line = hexa_add(hexa_add(line, hexa_str(" @link=")), link);
    }
    return line;
    return hexa_void();
}


HexaVal _hxi_let_line(HexaVal node, HexaVal mutable) {
    HexaVal prefix = (hexa_truthy(mutable) ? hexa_str("let_mut ") : hexa_str("let "));
    return hexa_add(hexa_add(prefix, hexa_to_string(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_629))), hexa_str(":_"));
    return hexa_void();
}


HexaVal emit_hxi(HexaVal ast, HexaVal src_bytes) {
    HexaVal lines = hexa_array_new();
    lines = hexa_array_push(lines, hexa_str("hxi v0"));
    lines = hexa_array_push(lines, hexa_add(hexa_str("src_bytes "), hexa_to_string(src_bytes)));
    HexaVal i = hexa_int(0);
    while (hexa_truthy(hexa_bool(__extension__ ({ HexaVal __l=(i); HexaVal __r=(hexa_int(hexa_len(ast))); (__l.tag==TAG_FLOAT||__r.tag==TAG_FLOAT) ? ((__l.tag==TAG_FLOAT?__l.f:(double)__l.i) < (__r.tag==TAG_FLOAT?__r.f:(double)__r.i)) : (__l.i < __r.i); })))) {
        HexaVal node = hexa_index_get(ast, i);
        HexaVal k = hexa_map_get_ic(node, "kind", &__hexa_codegen_c2_ic_630);
        if (hexa_truthy(hexa_eq(k, hexa_str("FnDecl")))) {
            lines = hexa_array_push(lines, _hxi_fn_line(node));
        } else {
            if (hexa_truthy(hexa_eq(k, hexa_str("PureFnDecl")))) {
                lines = hexa_array_push(lines, _hxi_fn_line(node));
            } else {
                if (hexa_truthy(hexa_eq(k, hexa_str("AsyncFnDecl")))) {
                    lines = hexa_array_push(lines, _hxi_fn_line(node));
                } else {
                    if (hexa_truthy(hexa_eq(k, hexa_str("StructDecl")))) {
                        lines = hexa_array_push(lines, _hxi_struct_line(node));
                    } else {
                        if (hexa_truthy(hexa_eq(k, hexa_str("EnumDecl")))) {
                            lines = hexa_array_push(lines, hexa_add(hexa_str("enum "), hexa_to_string(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_631))));
                        } else {
                            if (hexa_truthy(hexa_eq(k, hexa_str("ExternFnDecl")))) {
                                lines = hexa_array_push(lines, _hxi_extern_line(node));
                            } else {
                                if (hexa_truthy(hexa_eq(k, hexa_str("LetStmt")))) {
                                    lines = hexa_array_push(lines, _hxi_let_line(node, hexa_bool(0)));
                                } else {
                                    if (hexa_truthy(hexa_eq(k, hexa_str("LetMutStmt")))) {
                                        lines = hexa_array_push(lines, _hxi_let_line(node, hexa_bool(1)));
                                    } else {
                                        if (hexa_truthy(hexa_eq(k, hexa_str("ComptimeConst")))) {
                                            lines = hexa_array_push(lines, hexa_add(hexa_str("comptime "), hexa_to_string(hexa_map_get_ic(node, "name", &__hexa_codegen_c2_ic_632))));
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        i = hexa_add(i, hexa_int(1));
    }
    return hexa_add(hexa_str_join(lines, hexa_str("\n")), hexa_str("\n"));
    return hexa_void();
}


int _codegen_c2_init(int argc, char** argv) {
    hexa_set_args(argc, argv);
    _gen2_declared_names = hexa_array_new();
    _method_registry = hexa_array_new();
    _lambda_counter = hexa_int(0);
    _lambda_def_parts = hexa_array_new();
    _ic_counter = hexa_int(0);
    _ic_def_parts = hexa_array_new();
    _comptime_const_names = hexa_array_new();
    _comptime_const_nodes = hexa_array_new();
    _known_fn_globals = hexa_array_new();
    _known_nonlocal_names = hexa_array_new();
    hexa_println(hexa_str("=== HEXA → C (HexaVal runtime) Code Generator ==="));
    return 0;
}


int main(int argc, char** argv) {
    if (argc < 3) {
        printf("hexa-cc: HEXA self-hosted compiler\nUsage: hexa-cc <input.hexa> <output.c>\n");
        return 1;
    }
    hexa_set_args(argc, argv);
    HexaVal src = hexa_read_file(hexa_str(argv[1]));
    HexaVal tokens = tokenize(src);
    HexaVal ast = parse(tokens);
    HexaVal c_code = codegen_c2_full(ast);
    hexa_write_file(hexa_str(argv[2]), c_code);
    printf("OK: %s\n", argv[2]);
    return 0;
}
