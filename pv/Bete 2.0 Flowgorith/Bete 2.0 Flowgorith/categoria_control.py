from categoria_operatori import get_val
from categoria_utilitare import clean_name
from categoria_liste import proceseaza_bloc_lista
from categoria_evenimente import proceseaza_eveniment
from categoria_motion import translate_motion

def parse_blocks(target, blocks, start_id, var_types=None):
    if var_types is None:
        var_types = {}
        
    steps, v_found, l_found = [], set(), set()
    n_bool, n_in, max_d = False, False, 0
    curr = start_id

    while curr and curr in blocks:
        b = blocks[curr]
        op = b.get("opcode", "")
        inputs = b.get("inputs", {})

        if op.startswith("motion_"):
            steps.extend(translate_motion(op, inputs, target, blocks))
            v_found.update(["xpos", "ypos", "directie"])
        
        # --- SETARE VARIABILE CU INFERENȚĂ DE TIP ---
        elif op == "data_setvariableto" or op == "data_changevariableby":
            v_name = clean_name(b["fields"]["VARIABLE"][0])
            v_found.add(v_name)
            
            val_type = None
            inp = inputs.get("VALUE")
            
            if inp and isinstance(inp, list) and len(inp) >= 2:
                v = inp[1]
                if isinstance(v, list) and len(v) >= 2 and v[0] != 12:
                    val_str = str(v[1])
                    if val_str.lstrip('-').replace('.', '', 1).isdigit():
                        val_type = "Real"
                    else:
                        val_type = "String"
            
            if op == "data_changevariableby":
                val_type = "Real"
                
            if v_name not in var_types:
                var_types[v_name] = val_type if val_type else "Real"
                
            expected_type = var_types[v_name]
            
            val = get_val(target, blocks, inputs.get("VALUE"), expected_type)
            expr = val if op == "data_setvariableto" else f"{v_name} + {val}"
            steps.append(("assign", v_name, expr))

        elif op.startswith("data_") and "list" in op:
            res_l = proceseaza_bloc_lista(b, target, blocks)
            if res_l:
                steps.append(res_l)
                l_found.add(clean_name(b["fields"].get("LIST", ["lista"])[0]))

        elif op == "control_repeat":
            n_val = get_val(target, blocks, inputs.get("TIMES"), "Integer")
            inner = parse_blocks(target, blocks, inputs.get("SUBSTACK", [None, None])[1], var_types)
            steps.append(("for", n_val, inner[0]))
            v_found.update(inner[3]); l_found.update(inner[4])
            max_d = max(max_d, inner[5] + 1)

        elif op == "control_if" or op == "control_if_else":
            cond = get_val(target, blocks, inputs.get("CONDITION"), "Boolean")
            t_res = parse_blocks(target, blocks, inputs.get("SUBSTACK", [None, None])[1], var_types)
            e_res = parse_blocks(target, blocks, inputs.get("SUBSTACK2", [None, None])[1], var_types)
            steps.append(("if", cond, t_res[0], e_res[0]))
            v_found.update(t_res[3])
            v_found.update(e_res[3])
            l_found.update(t_res[4])
            l_found.update(e_res[4])
            max_d = max(max_d, t_res[5], e_res[5])

        elif op == "control_forever" or op == "control_repeat_until":
            n_bool = True
            inner = parse_blocks(target, blocks, inputs.get("SUBSTACK", [None, None])[1], var_types)
            cond = "true" if op == "control_forever" else f"NOT({get_val(target, blocks, inputs.get('CONDITION'), 'Boolean')})"
            steps.append(("while", cond, inner[0]))
            v_found.update(inner[3]); l_found.update(inner[4])
            max_d = max(max_d, inner[5])

        elif op == "sensing_askandwait":
            n_in = True
            steps.append(("output", get_val(target, blocks, inputs.get("QUESTION"), "String")))
            steps.append(("input", "raspunsscratch"))

        elif "looks_say" in op:
            steps.append(("output", get_val(target, blocks, inputs.get("MESSAGE"), "String")))
            
        elif op.startswith("event_broadcast"):
            res_e = proceseaza_eveniment(b, target, blocks)
            if res_e:
                if isinstance(res_e, list):
                    steps.extend(res_e)
                else:
                    steps.append(res_e)

        elif op == "procedures_call":
            if "custom_block" in b.get("inputs", {}):
                proc_id = b["inputs"]["custom_block"][1]
                if proc_id and proc_id in blocks:
                    proc_def = blocks[proc_id]
                    if proc_def.get("opcode") == "procedures_definition":
                        proto_id = proc_def["inputs"]["custom_block"][1]
                        if proto_id and proto_id in blocks:
                            proto = blocks[proto_id]
                            if "mutation" in proto:
                                proccode = proto["mutation"].get("proccode", "").split(" ")[0]
                                proc_name = clean_name(proccode)
                                steps.append(("output", f'"{proc_name}"'))

        elif op == "control_wait":
            duration = get_val(target, blocks, inputs.get("DURATION"), "Real")
            steps.append(("output", f'"Asteptand " & {duration} & " secunde"'))

        elif op == "control_stop":
            steps.append(("output", '"Program oprit"'))

        elif op == "sensing_touchingobject":
            obj = get_val(target, blocks, inputs.get("TOUCHINGOBJECTMENU"), "String")
            steps.append(("output", f'"Se atinge " & {obj}'))

        elif op in ["sensing_loudness", "sensing_timer"]:
            v_name = op.split("_")[1]
            v_found.add(v_name)
            steps.append(("assign", v_name, "0"))

        elif op in ["looks_show", "looks_hide"]:
            state = "visible" if op == "looks_show" else "ascuns"
            steps.append(("output", f'"Sprite {state}"'))

        elif op == "looks_changesize":
            size = get_val(target, blocks, inputs.get("CHANGE"), "Real")
            v_name = "size"
            v_found.add(v_name)
            steps.append(("assign", v_name, f"{v_name} + {size}"))

        elif op == "looks_setsize":
            size = get_val(target, blocks, inputs.get("SIZE"), "Real")
            v_name = "size"
            v_found.add(v_name)
            steps.append(("assign", v_name, size))

        elif op.startswith("sound_"):
            steps.append(("output", f'"Sunet: {op}"'))

        curr = b.get("next")
    return steps, n_bool, n_in, v_found, l_found, max_d