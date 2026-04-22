import os
import xml.etree.ElementTree as ET
from categoria_utilitare import load_scratch, clean_name
from categoria_control import parse_blocks

def build_xml_logic(parent, step_list, library, loop_vars, depth=0):
    for s in step_list:
        if s[0] == "assign":
            ET.SubElement(parent, "assign", variable=s[1], expression=s[2])
        elif s[0] == "call":
            ET.SubElement(parent, "call", expression=f"{s[1]}()")
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
            f_node = ET.SubElement(parent, "for", variable=loop_vars[depth % 4], start="1", end=s[1], direction="inc", step="1")
            build_xml_logic(f_node, s[2], library, loop_vars, depth + 1)
        elif s[0] == "while":
            w_node = ET.SubElement(parent, "while", expression=s[1])
            build_xml_logic(w_node, s[2], library, loop_vars, depth)
        elif s[0] == "if":
            i_node = ET.SubElement(parent, "if", expression=s[1])
            build_xml_logic(ET.SubElement(i_node, "then"), s[2], library, loop_vars, depth)
            build_xml_logic(ET.SubElement(i_node, "else"), s[3], library, loop_vars, depth)

def declare_strict_locals(parent_body, res, loop_vars, all_v, all_l):
    """Declară STRICT doar variabilele speciale și de buclă (toate variabilele sunt globale în Main)."""
    steps, needs_bool, needs_in, v_found, l_found, max_d = res
    
    if needs_bool: ET.SubElement(parent_body, "declare", name="running", type="Boolean", array="False", size="")
    if needs_in: ET.SubElement(parent_body, "declare", name="raspunsscratch", type="String", array="False", size="")
    
    # Nu mai declarăm v_found și l_found aici, sunt toate globale în Main
            
    for i in range(min(max_d, 4)):
        ET.SubElement(parent_body, "declare", name=loop_vars[i], type="Integer", array="False", size="")

def make_fprg(data, out_file):
    root = ET.Element("flowgorithm", fileversion="4.2")
    ET.SubElement(root, "attributes")
    main_func = ET.SubElement(root, "function", name="Main", type="None", variable="")
    ET.SubElement(main_func, "parameters")
    main_body = ET.SubElement(main_func, "body")
    loop_vars, library = ["i", "j", "k", "l"], {}
    all_v, all_l = set(), set()

    # Colectează TOATE variabilele și listele din toate target-urile
    for target in data["targets"]:
        blocks = target["blocks"]
        for b_id, b in blocks.items():
            if not isinstance(b, dict): continue
            if b.get("opcode") == "procedures_definition":
                if "custom_block" in b.get("inputs", {}):
                    res = parse_blocks(target, blocks, b.get("next"))
                    all_v.update(res[3])
                    all_l.update(res[4])
            elif b.get("opcode") == "event_whenbroadcastreceived":
                res = parse_blocks(target, blocks, b.get("next"))
                all_v.update(res[3])
                all_l.update(res[4])
        start_id = next((id for id, b in blocks.items() if isinstance(b, dict) and b.get("opcode") == "event_whenflagclicked"), None)
        if start_id:
            res = parse_blocks(target, blocks, blocks[start_id].get("next"))
            all_v.update(res[3])
            all_l.update(res[4])

    # Declară TOATE variabilele globale în Main
    for v in sorted(all_v):
        ET.SubElement(main_body, "declare", name=v, type="Real", array="False", size="")
        if v == "directie": ET.SubElement(main_body, "assign", variable=v, expression="90")
        elif v in ["xpos", "ypos"]: ET.SubElement(main_body, "assign", variable=v, expression="0")
    for lst in sorted(all_l):
        ET.SubElement(main_body, "declare", name=lst, type="Integer", array="True", size="500")
        ET.SubElement(main_body, "declare", name=f"idx{lst}", type="Integer", array="False", size="")
        ET.SubElement(main_body, "assign", variable=f"idx{lst}", expression="0")

    for target in data["targets"]:
        blocks = target["blocks"]
        for b_id, b in blocks.items():
            if not isinstance(b, dict): continue
            
            # Proceduri (My Blocks)
            if b.get("opcode") == "procedures_definition":
                proto_id = b["inputs"]["custom_block"][1]
                name = clean_name(blocks[proto_id]["mutation"]["proccode"].split(" ")[0])
                res = parse_blocks(target, blocks, b.get("next"))
                f_node = ET.SubElement(root, "function", name=name, type="None", variable="")
                ET.SubElement(f_node, "parameters")
                f_body = ET.SubElement(f_node, "body")
                declare_strict_locals(f_body, res, loop_vars, all_v, all_l)
                build_xml_logic(f_body, res[0], library, loop_vars)
            
            # Mesaje (Broadcast Received)
            elif b.get("opcode") == "event_whenbroadcastreceived":
                name = "Mesaj" + clean_name(b["fields"]["BROADCAST_OPTION"][0])
                res = parse_blocks(target, blocks, b.get("next"))
                m_node = ET.SubElement(root, "function", name=name, type="None", variable="")
                ET.SubElement(m_node, "parameters")
                m_body = ET.SubElement(m_node, "body")
                declare_strict_locals(m_body, res, loop_vars, all_v, all_l)
                build_xml_logic(m_body, res[0], library, loop_vars)

        # Flag Clicked (Punctul de intrare pentru Sprite)
        start_id = next((id for id, b in blocks.items() if isinstance(b, dict) and b.get("opcode") == "event_whenflagclicked"), None)
        if start_id:
            res = parse_blocks(target, blocks, blocks[start_id].get("next"))
            s_name = ("Stage" if target.get("isStage") else "Sprite") + clean_name(target["name"])
            s_node = ET.SubElement(root, "function", name=s_name, type="None", variable="")
            ET.SubElement(s_node, "parameters")
            s_body = ET.SubElement(s_node, "body")
            declare_strict_locals(s_body, res, loop_vars, all_v, all_l)
            build_xml_logic(s_body, res[0], library, loop_vars)
            ET.SubElement(main_body, "call", expression=f"{s_name}()")

    tree = ET.ElementTree(root)
    with open(out_file, "wb") as f:
        f.write(b'<?xml version="1.0"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        make_fprg(load_scratch(os.path.join(script_dir, "p2.sb3")), os.path.join(script_dir, "output.fprg"))
        print("Done.")
    except Exception as e: print(f"Error: {e}")