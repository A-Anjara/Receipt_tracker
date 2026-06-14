import os
from PIL import Image, ImageEnhance, ImageOps
import pytesseract
import requests
import json
import base64
from io import BytesIO
import re
from datetime import datetime , timedelta, timezone, date
import sqlite3
def save_db(data:dict,name:str):
    total = 0
    print("Expenses sum...")
    # Somme de la dépense
    for k,v in data["depenses"].items():
        total += v
    # Somme des charges
    print("Charges sum...")
    if("charges" in data):
        for k,v in data["charges"].items():
            total += v

    print("Managing date...")
    # Gestion de date
    is_date = bool(re.match(r"\d{4}-\d{2}-\d{2}",str(data["date"])))
    if(not is_date):
        current_date = datetime.now().date().isoformat()
    else:
        current_date = data["date"]

    print("Identifying file path...")
    filepath = f'{data["type"]}/{name}'
    
    # Insertion dans base de donnée
    print("Save to Database...")
    with sqlite3.connect('db.sql') as con:
        cur = con.cursor()
        cur.execute("""
        INSERT INTO RECEIPTS (title,total,date,json,type,file) VALUES 
        (?,?,?,?,?,?)
        """,(data["titre"], f"{total:.2f}", current_date, json.dumps(data), data["type"], filepath))
        print("Commiting Save...")
        con.commit()


def send_open_router(data_url):
    MODEL_NAME = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    OPENROUTER_API_KEY = "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"
    prompt_user = """
Vous êtes un expert en extraction de données financières. Analysez l'image du document financier fourni (reçu, facture, relevé, bon de commande, devis, etc.) et retournez UNIQUEMENT un JSON valide, sans texte supplémentaire avant ou après.

# Format de sortie obligatoire
{
  "titre": "titre court 3-6 mots",
  "date": "yyyy-mm-dd",
  "depenses": {
    "NOM_ARTICLE": valeur_numerique
  },
  "charges": {
    "NOM_CHARGE": valeur_numerique
  },
  "type": "recu|facture|facture_pro"
}

# Règles d'extraction

**titre** : 3 à 6 mots résumant l'objet de l'achat.

**date** : extraire la date du document au format yyyy-mm-dd.
Retourner null si la date est absente, illisible ou impossible à déterminer.

**depenses** : lister uniquement les produits et services achetés avec leur prix.
Ne jamais inclure les taxes, frais, pourboires ou remises ici.
Si aucune ligne d'article n'est visible, utiliser {"Total": montant_total_hors_charges}.

**charges** : lister séparément les charges additionnelles : taxes, frais de livraison, frais de service, pourboires, remises, suppléments.
Utiliser le libellé exact tel qu'il apparaît sur le document.
Si aucune charge n'existe, retourner un objet vide {}.

**type** : classifier le document selon ces règles :
- "recu" → paiement déjà effectué ou document de point de vente
- "facture" → demande de paiement (abonnement, utilitaire, service)
- "facture_pro" → facture formelle entre entreprises (B2B)
- Par défaut si aucun cas ne correspond → "recu"

# Contraintes absolues
- Retourner JSON uniquement, aucun commentaire ni texte autour
- Les prix sont des valeurs numériques pures, sans symbole de devise
- "titre", "type" et "depenses" ne peuvent jamais être vides ou null
- Le JSON doit être valide et correctement formaté
"""
    print("Envoi...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    ## HEADERS
    headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
    }
    
    messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": prompt_user
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": data_url
                }
            }
        ]
    }
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages
    }
    response = requests.post(url, headers=headers, json=payload)
    print("Received...")
    response = response.json()
    response = response["choices"][0]['message']['content']
    print("Extracting JSON...")
    match = re.search(r"(?s)\{.*}",response)
    response = match.group()
    response = json.loads(response)
    return response
    

def prepare_image(image:Image):
    print("Sauvegarde dans Buffer...")
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    print("Encodage base64...")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"
    

def process_file(image:Image,name:str):
    try:
        # Transform to RGBA then Black&White
        print("Conversion de l'image brute...")
        img = image.convert('RGBA').convert('L')

        # Enhancing image + contrast
        print("Contraste et Accentuation...")
        enhancer = ImageEnhance.Contrast(img)
        high_contrast_img = enhancer.enhance(2.5)

        # Buffering et Preparer L'envoi
        data_url = prepare_image(high_contrast_img)

        # Send to AI
        response = send_open_router(data_url)

        #Save in database
        save_db(response,name)

        print("Save success...")
        image.save(f"documents/{response['type']}/{name}")
        print("File saved...")
        return True
    except:
        return False