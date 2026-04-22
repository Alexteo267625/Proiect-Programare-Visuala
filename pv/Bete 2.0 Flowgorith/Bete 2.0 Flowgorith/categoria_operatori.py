from xml.sax.saxutils import escape
from categoria_utilitare import clean_name

def get_val(target, blocks, inp):
    """
    Traduce input-urile Scratch în expresii valide pentru Flowgorithm.
    """
    if not inp or not isinstance(inp, list) or len(inp) < 2:
        return "0"

    v = inp[1]

    # 1. VALORI DIRECTE (Numere, String-uri sau referințe de meniu)
    if isinstance(v, list):
        if len(v) >= 2 and v[0] == 12: # Variabilă din dropdown
            return clean_name(v[1])
        
        if len(v) >= 2:
            val_str = str(v[1])
            # Verificăm dacă este numeric (pentru a evita ghilimelele)
            is_numeric = val_str.lstrip('-').replace('.', '', 1).isdigit()
            
            if is_numeric:
                return val_str
            else:
                return f'"{escape(val_str)}"'

    # 2. PROCESARE BLOCURI (OPCODES)
    if isinstance(v, str) and v in blocks:
        b = blocks[v]
        op = b['opcode']
        inputs = b.get("inputs", {})

        # --- OPERATORI MATEMATICI DE BAZĂ ---
        math_basic = {
            "operator_add": "+",
            "operator_subtract": "-",
            "operator_multiply": "*",
            "operator_divide": "/"
        }
        if op in math_basic:
            o1 = get_val(target, blocks, inputs.get('NUM1'))
            o2 = get_val(target, blocks, inputs.get('NUM2'))
            return f"({o1} {math_basic[op]} {o2})"

        # --- MODULO ȘI ROUND ---
        if op == "operator_mod":
            n1 = get_val(target, blocks, inputs.get('NUM1'))
            n2 = get_val(target, blocks, inputs.get('NUM2'))
            return f"({n1} MOD {n2})"

        if op == "operator_round":
            n = get_val(target, blocks, inputs.get('NUM'))
            return f"Int({n} + 0.5)"

        # --- MATHOP (abs, sqrt, sin, cos, etc.) ---
        if op == "operator_mathop":
            func = b["fields"]["OPERATOR"][0].lower()
            val = get_val(target, blocks, inputs.get('NUM'))
            
            # Mapare funcții Scratch -> Flowgorithm
            # Notă: sin/cos/tan în Flowgorithm cer Radiani
            m_map = {
                "abs": f"Abs({val})",
                "sqrt": f"Sqrt({val})",
                "floor": f"Int({val})",
                "ceiling": f"(-Int(-{val}))",
                "sin": f"Sin({val} * PI / 180)",
                "cos": f"Cos({val} * PI / 180)",
                "tan": f"Tan({val} * PI / 180)",
                "asin": f"(Arcsin({val}) * 180 / PI)",
                "acos": f"(Arccos({val}) * 180 / PI)",
                "atan": f"(Arctan({val}) * 180 / PI)",
                "ln": f"Log({val})",
                "log": f"(Log({val}) / Log(10))",
                "e ^": f"Exp({val})",
                "10 ^": f"(10 ^ {val})"
            }
            return m_map.get(func, val)

        # --- OPERATORI LOGICI ȘI COMPARAȚII ---
        comp_map = {"operator_gt": ">", "operator_lt": "<", "operator_equals": "="}
        if op in comp_map:
            o1 = get_val(target, blocks, inputs.get('OPERAND1') or inputs.get('NUM1'))
            o2 = get_val(target, blocks, inputs.get('OPERAND2') or inputs.get('NUM2'))
            return f"({o1} {comp_map[op]} {o2})"

        if op == "operator_and":
            return f"({get_val(target, blocks, inputs.get('OPERAND1'))} && {get_val(target, blocks, inputs.get('OPERAND2'))})"
        if op == "operator_or":
            return f"({get_val(target, blocks, inputs.get('OPERAND1'))} || {get_val(target, blocks, inputs.get('OPERAND2'))})"
        if op == "operator_not":
            return f"NOT({get_val(target, blocks, inputs.get('OPERAND'))})"

        # --- OPERATORI DE TEXT ---
        if op == "operator_join":
            ##print(f"DEBUG: Inputs pentru join sunt: {inputs.keys()}")
            s1 = get_val(target, blocks, inputs.get('STRING1'))
            s2 = get_val(target, blocks, inputs.get('STRING2'))
            return f"({s1} & {s2})"

        if op == "operator_length":
            s = get_val(target, blocks, inputs.get('STRING'))
            return f"Len({s})"

        if op == "operator_letter_of":
            i = get_val(target, blocks, inputs.get('LETTER'))
            s = get_val(target, blocks, inputs.get('STRING'))
            return f"Char({s}, ({i}) - 1)"

        if op == "operator_contains":
            s1 = get_val(target, blocks, inputs.get('STRING1')) # haystack
            s2 = get_val(target, blocks, inputs.get('STRING2')) # needle
            return f"(InStr({s2}, {s1}) >= 0)"

        # --- ALTE REPORTERS (Random, Sensing, Motion) ---
        if op == "operator_random":
            f = get_val(target, blocks, inputs.get('FROM'))
            t = get_val(target, blocks, inputs.get('TO'))
            return f"(Random({t} - {f} + 1) + {f})"

        if op == "sensing_answer":
            return "raspunsscratch"

        if op == "data_variable":
            return clean_name(b["fields"]["VARIABLE"][0])
        
        # --- LISTE (item of list, length of list) ---
        if op in ["data_itemoflist", "data_lengthoflist"]:
            from categoria_liste import extrage_valoare_lista
            return extrage_valoare_lista(op, inputs, target, blocks)
        
        # Coordonate Sprite (Motion)
        motion_map = {"motion_xposition": "xpos", "motion_yposition": "ypos", "motion_direction": "directie"}
        if op in motion_map:
            return motion_map[op]

    return "0"