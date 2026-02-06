#!/usr/bin/env python3
"""Create beta tester accounts in Supabase."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

BETA_USERS = [
    {"email": "aaron.waite@gmail.com", "first_name": "Aaron", "last_name": "Waite"},
    {"email": "mdecourcey@waringvision.com", "first_name": "Michael", "last_name": "DeCourcey"},
    {"email": "gregory.parkhurst@gmail.com", "first_name": "Greg", "last_name": "Parkhurst"},
    {"email": "sbarnes@staar.com", "first_name": "Scott", "last_name": "Barnes"},
    {"email": "tajnassermd@gmail.com", "first_name": "Taj", "last_name": "Nasser"},
]

PASSWORD = "ICLVaultBeta"

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

for user in BETA_USERS:
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers=headers,
        json={
            "email": user["email"],
            "password": PASSWORD,
            "email_confirm": True,
            "user_metadata": {
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "full_name": f"{user['first_name']} {user['last_name']}",
            },
        },
    )

    if resp.status_code in (200, 201):
        print(f"✅ {user['email']} — created")
    elif resp.status_code == 422:
        print(f"⚠️  {user['email']} — already exists")
    else:
        print(f"❌ {user['email']} — {resp.status_code}: {resp.text}")

print("\nDone! All users can log in at https://iclvault.com with password: ICLVaultBeta")
