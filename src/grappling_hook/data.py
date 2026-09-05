import json
import os
import appdirs

config_path = f"{appdirs.user_data_dir(appname="grappling_hook")}/config.json"
template = {
    "save_path": "~/Downloads",
    "aniworld_path": "aniworld",
    # aniworld errors out instead of falling back, so a missing dub never downloads silently in another language
    "language": "German Dub",
}

def save(data):
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(data, f, indent=4)

def load():
    if not os.path.exists(config_path):
        save(template)
    with open(config_path) as f:
        data = json.load(f)
    for key in template:
        if key not in data:
            data[key] = template[key]
    save(data)
    with open(config_path) as f:
        return json.load(f)


data = load()

if __name__ == "__main__":
    print(load())
