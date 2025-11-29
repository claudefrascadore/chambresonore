# validate_room_and_matrix.py
# ----------------------------------------------------------
# Validation des dimensions de la pièce et de la matrice.
# Le but :
#   - empêcher la matrice de dépasser la pièce
#   - corriger automatiquement les valeurs invalides
#   - produire un message d’erreur COURT (affiché dans l’UI)
#   - garder les valeurs persistantes et cohérentes
#
# Paramètres :
#   width_m      : largeur de la pièce (float)
#   depth_m      : profondeur de la pièce (float)
#   cols_input   : colonnes demandées (int)
#   rows_input   : rangées demandées (int)
#
# Retour :
#   {
#     "width": width corrigée,
#     "depth": depth corrigée,
#     "cols": cols corrigées,
#     "rows": rows corrigées,
#     "message": message court ou ""
#   }
#
# NOTE :
#   - La cellule fait toujours 1 m × 1 m.
#   - Les valeurs width/depth NE SONT PAS modifiées ici, sauf si < 1.
#   - cols_max = floor(width)
#   - rows_max = floor(depth)
# ----------------------------------------------------------

import math

def validate_room_and_matrix(width_m, depth_m, cols_input, rows_input):
    message = ""

    # Assurer que la pièce n’a pas de dimension invalide
    if width_m < 1.0:
        width_m = 1.0
        message = "Largeur trop petite. Ramenée à 1,0."
    if depth_m < 1.0:
        depth_m = 1.0
        if not message:
            message = "Profondeur trop petite. Ramenée à 1,0."
        else:
            message += " Profondeur trop petite. Ramenée à 1,0."

    # Calcul des limites maximales selon la pièce
    cols_max = math.floor(width_m)
    rows_max = math.floor(depth_m)

    # Valeurs corrigées, basées sur l’entrée utilisateur
    cols = cols_input
    rows = rows_input

    # Validation colonnes
    if cols_input > cols_max:
        cols = cols_max
        message = f"Dépassement de largeur ({cols_input}). Valeur ramenée à {cols_max}."

    # Validation rangées
    if rows_input > rows_max:
        # Si un message existe déjà, on ajoute une deuxième phrase
        if message:
            message += f" Pièce de {depth_m:.1f} m. Valeur ramenée à {rows_max}."
        else:
            message = f"Pièce de {depth_m:.1f} m. Valeur ramenée à {rows_max}."
        rows = rows_max

    return {
        "width": width_m,
        "depth": depth_m,
        "cols": cols,
        "rows": rows,
        "message": message
    }

