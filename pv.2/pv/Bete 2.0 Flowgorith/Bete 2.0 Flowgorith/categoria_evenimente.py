from categoria_utilitare import clean_name
from categoria_operatori import get_val


def proceseaza_eveniment(b, target, blocks):
    op = b["opcode"]
    inputs = b.get("inputs", {})

    # --- BROADCAST (TRIMITE MESAJ) ---
    if op in ["event_broadcast", "event_broadcastandwait"]:
        # Extragem numele mesajului din input
        msg_val = get_val(target, blocks, inputs.get("BROADCAST_INPUT"))

        # Curățăm numele: scoatem ghilimelele și folosim clean_name (care elimină și _)
        nume_mesaj = clean_name(msg_val.replace('"', ''))

        # Returnăm apelul FĂRĂ underscore, pentru a se potrivi cu funcțiile generate în main.py
        return ("call", f"Mesaj{nume_mesaj}")

    # --- ALTE EVENIMENTE (SIMULATE PRIN OUTPUT PENTRU LOGICĂ) ---
    elif op == "event_whenkeypressed":
        tasta = b["fields"]["KEY_OPTION"][0]
        return ("output", f'"Astept tasta: {tasta}"')

    elif op == "event_whenthisspriteclicked":
        return ("output", '"Sprite clicat"')

    elif op == "event_whenbackdropswitchesto":
        bg_name = b["fields"]["BACKDROP_VARIABLE"][0]
        return ("output", f'"Fundal schimbat la: {bg_name}"')

    return None