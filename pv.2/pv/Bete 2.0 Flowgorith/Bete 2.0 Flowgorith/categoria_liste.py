from categoria_utilitare import clean_name
from categoria_operatori import get_val


def proceseaza_bloc_lista(b, target, blocks):
    op = b["opcode"]
    inputs = b.get("inputs", {})

    # Numele listei din Scratch (trecut prin filtrul de curățare)
    if "LIST" in b["fields"]:
        list_name = clean_name(b["fields"]["LIST"][0])
    else:
        return None

    # --- ADĂUGARE ÎN LISTĂ ---
    if op == "data_addtolist":
        val = get_val(target, blocks, inputs.get("ITEM"))
        # Returnăm un tuplu pe care main.py îl va transforma în: list[idx] = val; idx = idx + 1
        return ("assign_list_add", list_name, val)

    # --- ȘTERGERE COMPLETĂ (RESETARE INDEX) ---
    elif op == "data_deletealloflist":
        return ("list_clear", list_name)

    # --- ÎNLOCUIRE ELEMENT LA INDEX ---
    elif op == "data_replaceitemoflist":
        idx = get_val(target, blocks, inputs.get("INDEX"))
        val = get_val(target, blocks, inputs.get("ITEM"))
        # Notă: Scratch începe de la 1, Flowgorithm de la 0.
        # Dacă vrei compatibilitate perfectă, poți folosi f"({idx}) - 1"
        return ("assign_list_idx", list_name, idx, val)

    return None


def extrage_valoare_lista(op, inputs, target, blocks):
    """
    Această funcție este apelată din categoria_operatori.py
    pentru a gestiona blocurile rotunde de tip listă.
    """
    # Extragem numele listei
    list_input = inputs.get("LIST")
    if not list_input:
        return "0"

    if isinstance(list_input, list) and list_input[0] == 12:
        list_name = clean_name(list_input[1])
    elif isinstance(list_input, str):
        list_name = clean_name(list_input)
    else:
        list_name = "lista"

    # Item X din listă
    if op == "data_itemoflist":
        idx = get_val(target, blocks, inputs.get("INDEX"))
        return f"{list_name}[{idx}]"

    # Lungimea listei
    if op == "data_lengthoflist":
        # În Flowgorithm folosim variabila indexului pentru a ști câte elemente am adăugat
        return f"idx{list_name}"

    return "0"