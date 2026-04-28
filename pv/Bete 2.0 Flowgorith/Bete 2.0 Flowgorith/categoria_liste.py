from categoria_utilitare import clean_name
from categoria_operatori import get_val

def proceseaza_bloc_lista(b, target, blocks):
    op = b["opcode"]
    inputs = b.get("inputs", {})

    # Numele listei din Scratch
    if "LIST" in b["fields"]:
        list_name = clean_name(b["fields"]["LIST"][0])
    else:
        return None

    # --- ADĂUGARE ÎN LISTĂ ---
    if op == "data_addtolist":
        # Flowgorithm arrays sunt declarate Integer; solicităm cast Integer
        val = get_val(target, blocks, inputs.get("ITEM"), "Integer")
        return ("assign_list_add", list_name, val)

    # --- ȘTERGERE COMPLETĂ ---
    elif op == "data_deletealloflist":
        return ("list_clear", list_name)

    # --- ÎNLOCUIRE ELEMENT ---
    elif op == "data_replaceitemoflist":
        idx = get_val(target, blocks, inputs.get("INDEX"), "Integer")
        val = get_val(target, blocks, inputs.get("ITEM"), "Integer")
        return ("assign_list_idx", list_name, idx, val)

    return None

def extrage_valoare_lista(b, target, blocks):
    op = b.get("opcode")
    inputs = b.get("inputs", {})
    fields = b.get("fields", {})

    if "LIST" in fields:
        list_name = clean_name(fields["LIST"][0])
    else:
        return "0"

    # --- ITEM X DIN LISTĂ ---
    if op == "data_itemoflist":
        # Indexul trebuie să fie numeric
        idx = get_val(target, blocks, inputs.get("INDEX"), "Integer")
        return f"{list_name}[({idx}) - 1]"

    # --- LUNGIMEA LISTEI ---
    if op == "data_lengthoflist":
        return f"idx{list_name}"

    return "0"