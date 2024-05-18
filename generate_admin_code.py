import bcrypt
import json


admin_code = "staff"  
hashed_admin_code = bcrypt.hashpw(admin_code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


data = {
    "admin_code_hash": hashed_admin_code
}

with open('config.json', 'w') as json_file:
    json.dump(data, json_file)

print("Admin code hash has been saved to config.json")
