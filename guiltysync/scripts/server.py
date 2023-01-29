from collections import defaultdict
import json
from typing import Dict, List

import click
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn


config_filepath = ""
config = {}


def write_config(config_path, config_data):
    global config

    with open(config_path, "w", encoding="UTF-8") as config_file:
        json.dump(config_data, config_file)

def ping():
    return


class UserData(BaseModel):
    member: str
    mods: Dict[str, Dict[str, str]]


def post_group(group: str, user_data: UserData):
    if group in config["groups"]:
        raise HTTPException(status_code=409, detail="Group already exists")
    config["groups"][group] = {}
    config["groups"][group][user_data.member] = user_data.mods

    write_config(config_filepath, config)


def post_group_member(group: str, member: str, user_data: UserData):
    try:
        config["groups"][group][member] = user_data.mods
    except KeyError:
        raise HTTPException(status_code=404, detail="Group not found")
    
    write_config(config_filepath, config)


def get_group(group: str):
    try:
        return config["groups"][group]
    except KeyError:
        raise HTTPException(status_code=404, detail="Group not found")


@click.option("--host", "-h", default="0.0.0.0")
@click.option("--port", "-p", type=int, default="6969")
@click.option("--config-path", "-c", default="config.json")
@click.command()
def server(host, port, config_path):
    global config, config_filepath

    config_filepath = config_path

    with open(config_filepath, "r", encoding="UTF=8") as config_file:
        config = json.load(config_file)

    app = FastAPI()

    app.add_api_route("/groups/{group}", post_group, methods=["POST"])
    app.add_api_route("/groups/{group}/{member}", post_group_member, methods=["PUT"])
    app.add_api_route("/groups/{group}", get_group, methods=["GET"])
    app.add_api_route("/", ping, methods=["GET"])

    uvicorn.run(app, host=host, port=port)
