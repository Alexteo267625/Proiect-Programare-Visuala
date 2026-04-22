from categoria_operatori import get_val
from categoria_utilitare import clean_name
from categoria_liste import proceseaza_bloc_lista
from categoria_evenimente import proceseaza_eveniment
from categoria_motion import translate_motion

def parse_blocks(target, blocks, start_id):
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
        
        elif op == "data_setvariableto" or op == "data_changevariableby":
            v_name = clean_name(b["fields"]["VARIABLE"][0])
            v_found.add(v_name)
            val = get_val(target, blocks, inputs.get("VALUE"))
            expr = val if op == "data_setvariableto" else f"{v_name} + {val}"
            steps.append(("assign", v_name, expr))

        elif op.startswith("data_") and "list" in op:
            res_l = proceseaza_bloc_lista(b, target, blocks)
            if res_l:
                steps.append(res_l)
                l_found.add(clean_name(b["fields"].get("LIST", ["lista"])[0]))

        elif op == "control_repeat":
            n_val = get_val(target, blocks, inputs.get("TIMES"))
            inner = parse_blocks(target, blocks, inputs.get("SUBSTACK", [None, None])[1])
            steps.append(("for", n_val, inner[0]))
            v_found.update(inner[3]); l_found.update(inner[4])
            max_d = max(max_d, inner[5] + 1)

        elif op == "control_if" or op == "control_if_else":
            cond = get_val(target, blocks, inputs.get("CONDITION"))
            t_res = parse_blocks(target, blocks, inputs.get("SUBSTACK", [None, None])[1])
            e_res = parse_blocks(target, blocks, inputs.get("SUBSTACK2", [None, None])[1])
            steps.append(("if", cond, t_res[0], e_res[0]))
            v_found.update(t_res[3])
            v_found.update(e_res[3])
            l_found.update(t_res[4])
            l_found.update(e_res[4])
            max_d = max(max_d, t_res[5], e_res[5])

        elif op == "control_forever" or op == "control_repeat_until":
            n_bool = True
            inner = parse_blocks(target, blocks, inputs.get("SUBSTACK", [None, None])[1])
            cond = "true" if op == "control_forever" else f"NOT({get_val(target, blocks, inputs.get('CONDITION'))})"
            steps.append(("while", cond, inner[0]))
            v_found.update(inner[3]); l_found.update(inner[4])
            max_d = max(max_d, inner[5])

        elif op == "sensing_askandwait":
            n_in = True
            steps.append(("output", get_val(target, blocks, inputs.get("QUESTION"))))
            steps.append(("input", "raspunsscratch"))

        elif "looks_say" in op:
            steps.append(("output", get_val(target, blocks, inputs.get("MESSAGE"))))
            
        elif op.startswith("event_broadcast"):
            res_e = proceseaza_eveniment(b, target, blocks)
            if res_e:
                if isinstance(res_e, list):
                    steps.extend(res_e)
                else:
                    steps.append(res_e)

        # --- PROCEDURI (CALL MY BLOCK) ---
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
                                steps.append(("output", proc_name))

        # --- WAIT BLOCK ---
        elif op == "control_wait":
            duration = get_val(target, blocks, inputs.get("DURATION"))
            steps.append(("output", f'"Asteptand {duration} secunde"'))

        # --- STOP BLOCK ---
        elif op == "control_stop":
            steps.append(("output", '"Program oprit"'))

        # --- SENSING BLOCKS ---
        elif op == "sensing_touchingobject":
            obj = get_val(target, blocks, inputs.get("TOUCHINGOBJECTMENU"))
            steps.append(("output", f'"Se atinge {obj}"'))

        elif op == "sensing_loudness":
            v_name = "loudness"
            v_found.add(v_name)
            steps.append(("assign", v_name, "0"))

        elif op == "sensing_timer":
            v_name = "timer"
            v_found.add(v_name)
            steps.append(("assign", v_name, "0"))

        # --- LOOKS BLOCKS ---
        elif op == "looks_show":
            steps.append(("output", '"Sprite visible"'))

        elif op == "looks_hide":
            steps.append(("output", '"Sprite ascuns"'))

        elif op == "looks_changesize":
            size = get_val(target, blocks, inputs.get("CHANGE"))
            v_name = "size"
            v_found.add(v_name)
            steps.append(("assign", v_name, f"{v_name} + {size}"))

        elif op == "looks_setsize":
            size = get_val(target, blocks, inputs.get("SIZE"))
            v_name = "size"
            v_found.add(v_name)
            steps.append(("assign", v_name, size))

        # --- SOUND BLOCKS ---
        elif op.startswith("sound_"):
            steps.append(("output", f'"Sunet: {op}"'))

        # --- UNKNOWN BLOCKS ---
        elif op and not op.startswith("comment"):
            # Dacă blocul nu este recunoscut, adaug un output pentru debug
            pass

        curr = b.get("next")
    return steps, n_bool, n_in, v_found, l_found, max_d