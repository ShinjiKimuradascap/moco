from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- Common Schemas ---

class CharacterBase(BaseModel):
    id: int
    master_id: int
    level: int
    exp: int
    star_rank: int
    shards: int

    model_config = ConfigDict(from_attributes=True)

class ItemBase(BaseModel):
    id: int
    master_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    id: int
    name: str
    paid_wings: int
    free_wings: int
    gold: int
    mileage: int
    stamina: int
    last_stamina_update: datetime

    model_config = ConfigDict(from_attributes=True)

class UserStatusResponse(UserBase):
    characters: List[CharacterBase]
    items: List[ItemBase]

# --- Gacha Schemas ---

class GachaRequest(BaseModel):
    user_id: int
    times: int # 1 or 10

class GachaResultItem(BaseModel):
    rarity: str
    detail: str
    master_id: int
    is_new: bool

class GachaResponse(BaseModel):
    results: List[GachaResultItem]
    new_mileage: int

# --- Match Schemas ---

class MatchRequest(BaseModel):
    user_id: int
    team_id: int

class MatchResponse(BaseModel):
    is_win: bool
    logs: List[str]
    rewards: dict # {"gold": int, "exp": int}

# --- Progression Schemas ---

class LevelUpRequest(BaseModel):
    user_id: int
    character_id: int
    gold_cost: int
    exp_amount: int

class StarUpRequest(BaseModel):
    user_id: int
    character_id: int
