from xml.sax.saxutils import escape
from categoria_utilitare import clean_name

def apply_cast(val, expected_type):
    """Aplică funcțiile de conversie Flowgorithm EXCLUSIV pentru raspunsscratch."""
    if not expected_type:
        return val
        
    # Dacă valoarea nu este raspunsscratch, returnăm codul curat (fără cast)
    if val != "raspunsscratch":
        return val

    # Convertim DOAR raspunsscratch în funcție de destinație
    if expected_type == "Integer":
        return f"toInteger({val})"
    elif expected_type == "Real":
        return f"toReal({val})" 
    elif expected_type == "Boolean":
        return f"toBoolean({val})"
    
    # Dacă se cere String, raspunsscratch e deja String nativ, îl lăsăm curat
    return val

def get_val(target, blocks, inp, expected_type=None):
    if not inp or not isinstance(inp, list) or len(inp) < 2:
        return apply_cast("0", expected_type)

    v = inp[1]

    # 1. VALORI DIRECTE
    if isinstance(v, list):
        if len(v) >= 2 and v[0] == 12: # Variabilă din dropdown
            return apply_cast(clean_name(v[1]), expected_type)
        
        if len(v) >= 2:
            val_str = str(v[1])
            is_numeric = val_str.lstrip('-').replace('.', '', 1).isdigit()
            
            if is_numeric:
                if expected_type == "String": return f'"{val_str}"'
                return apply_cast(val_str, expected_type)
            else:
                return f'"{escape(val_str)}"'

    # 2. PROCESARE BLOCURI (OPCODES)
    if isinstance(v, str) and v in blocks:
        b = blocks[v]
        op = b['opcode']
        inputs = b.get("inputs", {})

        def parse_inner(name, exp_t=None):
            return get_val(target, blocks, inputs.get(name), exp_t)

        res = "0"
        
        # --- MATEMATICA DE BAZĂ (cere numere Real) ---
        math_basic = {"operator_add": "+", "operator_subtract": "-", "operator_multiply": "*", "operator_divide": "/"}
        if op in math_basic:
            res = f"({parse_inner('NUM1', 'Real')} {math_basic[op]} {parse_inner('NUM2', 'Real')})"

        elif op == "operator_mod":
            res = f"({parse_inner('NUM1', 'Real')} MOD {parse_inner('NUM2', 'Real')})"

        elif op == "operator_round":
            res = f"toInteger({parse_inner('NUM', 'Real')} + 0.5)"

        elif op == "operator_mathop":
            func = b["fields"]["OPERATOR"][0].lower()
            val = parse_inner('NUM', "Real")
            m_map = {
                "abs": f"Abs({val})", "sqrt": f"Sqrt({val})", "floor": f"toInteger({val})",
                "ceiling": f"(-toInteger(-{val}))", "sin": f"Sin({val} * PI / 180)",
                "cos": f"Cos({val} * PI / 180)", "tan": f"Tan({val} * PI / 180)",
                "asin": f"(Arcsin({val}) * 180 / PI)", "acos": f"(Arccos({val}) * 180 / PI)",
                "atan": f"(Arctan({val}) * 180 / PI)", "ln": f"Log({val})",
                "log": f"(Log({val}) / Log(10))", "e ^": f"Exp({val})", "10 ^": f"(10 ^ {val})"
            }
            res = m_map.get(func, val)

        # --- COMPARAȚII INTELIGENTE ---
        elif op in ["operator_gt", "operator_lt", "operator_equals"]:
            cm = {"operator_gt": ">", "operator_lt": "<", "operator_equals": "="}
            
            inp1 = inputs.get('OPERAND1') or inputs.get('NUM1')
            inp2 = inputs.get('OPERAND2') or inputs.get('NUM2')
            
            def peek_is_string(inp_obj):
                if inp_obj and isinstance(inp_obj, list) and len(inp_obj) >= 2:
                    v_in = inp_obj[1]
                    if isinstance(v_in, list) and len(v_in) >= 2 and v_in[0] != 12:
                        return not str(v_in[1]).lstrip('-').replace('.', '', 1).isdigit()
                return False

            comp_type = "String" if (peek_is_string(inp1) or peek_is_string(inp2)) else "Real"
            
            o1 = get_val(target, blocks, inp1, comp_type)
            o2 = get_val(target, blocks, inp2, comp_type)
            
            res = f"({o1} {cm[op]} {o2})"

        # --- LOGICĂ (cere Boolean) ---
        elif op == "operator_and":
            res = f"({parse_inner('OPERAND1', 'Boolean')} && {parse_inner('OPERAND2', 'Boolean')})"
        elif op == "operator_or":
            res = f"({parse_inner('OPERAND1', 'Boolean')} || {parse_inner('OPERAND2', 'Boolean')})"
        elif op == "operator_not":
            res = f"NOT({parse_inner('OPERAND', 'Boolean')})"

        # --- TEXT (cere String) ---
        elif op == "operator_join":
            res = f"({parse_inner('STRING1', 'String')} & {parse_inner('STRING2', 'String')})"
        elif op == "operator_length":
            res = f"Len({parse_inner('STRING', 'String')})"
        elif op == "operator_letter_of":
            i = parse_inner('LETTER', 'Integer')
            res = f"Char({parse_inner('STRING', 'String')}, ({i}) - 1)"
        elif op == "operator_contains":
            res = f"(InStr({parse_inner('STRING2', 'String')}, {parse_inner('STRING1', 'String')}) >= 0)"

        # --- REPORTERS (Răspunsuri, Liste, Variabile) ---
        elif op == "operator_random":
            f = parse_inner('FROM', 'Integer')
            t = parse_inner('TO', 'Integer')
            res = f"(Random({t} - {f} + 1) + {f})"
        
        elif op == "sensing_answer":
            res = "raspunsscratch"
        
        elif op == "data_variable":
            res = clean_name(b["fields"]["VARIABLE"][0])
        
        elif op in ["data_itemoflist", "data_lengthoflist"]:
            from categoria_liste import extrage_valoare_lista
            res = extrage_valoare_lista(b, target, blocks)

        elif op in ["motion_xposition", "motion_yposition", "motion_direction"]:
            motion_map = {"motion_xposition": "xpos", "motion_yposition": "ypos", "motion_direction": "directie"}
            res = motion_map[op]
        
        return apply_cast(res, expected_type)

    return apply_cast("0", expected_type)