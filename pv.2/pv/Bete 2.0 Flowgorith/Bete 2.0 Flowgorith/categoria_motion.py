import math

def translate_motion(opcode, inputs, target, blocks):
    """
    Traduce blocurile de miscare Scratch in operatii matematice pentru Flowgorithm.
    Folosim get_val pentru a permite si variabile in interiorul blocurilor de miscare.
    """
    from categoria_operatori import get_val
    pasi = []

    if opcode == "motion_movesteps":
        # Conversie unghi: Scratch (0 deg = Sus) -> Flowgorithm (0 deg = Dreapta, radiani)
        distanta = get_val(target, blocks, inputs.get('STEPS'))
        pasi.append(("assign", "xpos", f"xpos + cos((90 - directie) * PI / 180) * {distanta}"))
        pasi.append(("assign", "ypos", f"ypos + sin((90 - directie) * PI / 180) * {distanta}"))

    elif opcode == "motion_gotoxy":
        new_x = get_val(target, blocks, inputs.get('X'))
        new_y = get_val(target, blocks, inputs.get('Y'))
        pasi.append(("assign", "xpos", new_x))
        pasi.append(("assign", "ypos", new_y))

    elif opcode == "motion_turnright":
        grade = get_val(target, blocks, inputs.get('DEGREES'))
        pasi.append(("assign", "directie", f"directie + {grade}"))

    elif opcode == "motion_turnleft":
        grade = get_val(target, blocks, inputs.get('DEGREES'))
        pasi.append(("assign", "directie", f"directie - {grade}"))

    elif opcode == "motion_pointindirection":
        unghi = get_val(target, blocks, inputs.get('DIRECTION'))
        pasi.append(("assign", "directie", unghi))

    return pasi