import os
import xml.etree.ElementTree as ET
from categoria_utilitare import load_scratch, clean_name
from categoria_control import parse_blocks

def build_xml_logic(parent, step_list, loop_vars, depth=0):
    """Transformă lista de pași (tupluri) în noduri XML Flowgorithm."""
    for s in step_list:
        if s[0] == "assign":
            ET.SubElement(parent, "assign", variable=s[1], expression=s[2])
        elif s[0] == "assign_list_add":
            idx_v = f"idx{s[1]}"
            ET.SubElement(parent, "assign", variable=f"{s[1]}[{idx_v}]", expression=s[2])
            ET.SubElement(parent, "assign", variable=idx_v, expression=f"{idx_v} + 1")
        elif s[0] == "assign_list_idx":
            ET.SubElement(parent, "assign", variable=f"{s[1]}[({s[2]})-1]", expression=s[3])
        elif s[0] == "list_clear":
            ET.SubElement(parent, "assign", variable=f"idx{s[1]}", expression="0")
        elif s[0] == "output":
            ET.SubElement(parent, "output", expression=s[1])
        elif s[0] == "input":
            ET.SubElement(parent, "input", variable=s[1])
        elif s[0] == "for":
            # Folosim variabile de buclă i, j, k, l în funcție de adâncime
            var_name = loop_vars[depth % 4]
            f_node = ET.SubElement(parent, "for", variable=var_name, 
                                   start="1", end=s[1], direction="inc", step="1")
            build_xml_logic(f_node, s[2], loop_vars, depth + 1)
        elif s[0] == "while":
            w_node = ET.SubElement(parent, "while", expression=s[1])
            build_xml_logic(w_node, s[2], loop_vars, depth)
        elif s[0] == "if":
            i_node = ET.SubElement(parent, "if", expression=s[1])
            build_xml_logic(ET.SubElement(i_node, "then"), s[2], loop_vars, depth)
            build_xml_logic(ET.SubElement(i_node, "else"), s[3], loop_vars, depth)

def make_fprg(data, out_file):
    root = ET.Element("flowgorithm", fileversion="4.2")
    ET.SubElement(root, "attributes")
    
    # Creează funcția Main - singura care va conține toată logica
    main_func = ET.SubElement(root, "function", name="Main", type="None", variable="")
    ET.SubElement(main_func, "parameters")
    main_body = ET.SubElement(main_func, "body")

    loop_vars = ["i", "j", "k", "l"]
    all_steps = []
    g_vars = set()
    g_lists = set()
    n_bool, n_in, m_depth = False, False, 0

    # --- 1. SCANARE TOTALĂ VARIABILE ȘI LISTE ---
    for target in data["targets"]:
        # Extragem variabilele definite în meniul Scratch
        if "variables" in target:
            for v_id, v_info in target["variables"].items():
                g_vars.add(clean_name(v_info[0]))
        # Extragem listele
        if "lists" in target:
            for l_id, l_info in target["lists"].items():
                g_lists.add(clean_name(l_info[0]))

    # --- 2. COLECTARE LOGICĂ DIN TOATE PERSONAJELE (SPRITES) ---
    for target in data["targets"]:
        blocks = target["blocks"]
        
        # A. Căutăm STEAGUL VERDE (Punctul de start principal)
        for b_id, b in blocks.items():
            if isinstance(b, dict) and b.get("opcode") == "event_whenflagclicked":
                res = parse_blocks(target, blocks, b.get("next"))
                all_steps.extend(res[0])
                n_bool |= res[1]; n_in |= res[2]; m_depth = max(m_depth, res[5])
                g_vars.update(res[3])

        # B. Căutăm CLONELE (When I start as a clone)
        for b_id, b in blocks.items():
            if isinstance(b, dict) and b.get("opcode") == "control_start_as_clone":
                all_steps.append(("output", f'"--- START CLONA: {target["name"]} ---"'))
                res = parse_blocks(target, blocks, b.get("next"))
                all_steps.extend(res[0])
                n_bool |= res[1]; n_in |= res[2]; m_depth = max(m_depth, res[5]); g_vars.update(res[3])

        # C. Căutăm MESAJELE (When I receive broadcast)
        for b_id, b in blocks.items():
            if isinstance(b, dict) and b.get("opcode") == "event_whenbroadcastreceived":
                msg_val = b["fields"]["BROADCAST_OPTION"][0]
                all_steps.append(("output", f'"--- MESAJ PRIMIT: {msg_val} ---"'))
                res = parse_blocks(target, blocks, b.get("next"))
                all_steps.extend(res[0])
                n_bool |= res[1]; n_in |= res[2]; m_depth = max(m_depth, res[5]); g_vars.update(res[3])

    # --- 3. DECLARAȚII ÎN MAIN (O singură dată, la început) ---
    if n_bool: ET.SubElement(main_body, "declare", name="running", type="Boolean", array="False", size="")
    if n_in: ET.SubElement(main_body, "declare", name="raspunsscratch", type="String", array="False", size="")
    
    # Variabile numerice (Real)
    for v in sorted(g_vars):
        ET.SubElement(main_body, "declare", name=v, type="Real", array="False", size="")
        # Inițializare specială pentru direcție
        init_val = "90" if v == "directie" else "0"
        ET.SubElement(main_body, "assign", variable=v, expression=init_val)

    # Liste (Arrays)
    for lst in sorted(g_lists):
        ET.SubElement(main_body, "declare", name=lst, type="Integer", array="True", size="500")
        ET.SubElement(main_body, "declare", name=f"idx{lst}", type="Integer", array="False", size="")
        ET.SubElement(main_body, "assign", variable=f"idx{lst}", expression="0")

    # Variabile de buclă (i, j, k, l)
    for i in range(min(m_depth + 1, 4)):
        ET.SubElement(main_body, "declare", name=loop_vars[i], type="Integer", array="False", size="")

    # --- 4. CONSTRUIRE LOGICĂ EXECUTABILĂ ---
    build_xml_logic(main_body, all_steps, loop_vars)

    # --- 5. SALVARE FIȘIER ---
    tree = ET.ElementTree(root)
    with open(out_file, "wb") as f:
        f.write(b'<?xml version="1.0"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "p2.sb3")
    output_file = os.path.join(script_dir, "output.fprg")
    
    try:
        make_fprg(load_scratch(input_file), output_file)
        print(f"Gata! Verifică {output_file}. Clonele și mesajele au fost incluse.")
    except Exception as e:
        print(f"Eroare: {e}")