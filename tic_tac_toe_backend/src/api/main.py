from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import uuid


app = FastAPI(
    title="Tic Tac Toe Backend API",
    description=(
        "A FastAPI backend for Tic Tac Toe game. Handles game logic, state "
        "management, and exposes APIs for game operations."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "Game", "description": "Tic Tac Toe Game Operations"},
    ],
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NewGameResponse(BaseModel):
    """Response for starting a game."""
    game_id: str = Field(..., description="Unique game session ID")
    board: list[list[str]] = Field(
        ..., description="3x3 Tic Tac Toe board"
    )
    current_player: str = Field(..., description="'X' or 'O'")
    status: str = Field(..., description="Game status: ongoing, win, or draw")
    winner: Optional[str] = Field(
        None, description="'X', 'O', or None if no winner"
    )


class MoveRequest(BaseModel):
    """Request for making a move."""
    row: int = Field(
        ..., ge=0, le=2, description="Row index (0-2)"
    )
    col: int = Field(
        ..., ge=0, le=2, description="Column index (0-2)"
    )


class MoveResponse(BaseModel):
    """Response for a move request."""
    board: list[list[str]] = Field(
        ..., description="Updated 3x3 Tic Tac Toe board"
    )
    current_player: Optional[str] = Field(
        None, description="Next player, or None if game over"
    )
    status: str = Field(
        ..., description="Game status: ongoing, win, or draw"
    )
    winner: Optional[str] = Field(
        None, description="'X', 'O', or None if no winner"
    )


class GameStateResponse(BaseModel):
    """Current state of a game."""
    game_id: str = Field(
        ..., description="Unique game session ID"
    )
    board: list[list[str]] = Field(
        ..., description="3x3 Tic Tac Toe board"
    )
    current_player: Optional[str] = Field(
        None, description="'X', 'O', or None if game over"
    )
    status: str = Field(
        ..., description="Game status: ongoing, win, or draw"
    )
    winner: Optional[str] = Field(
        None, description="'X', 'O', or None if no winner"
    )


games: Dict[str, dict] = {}


def _new_board() -> list[list[str]]:
    """Return a new blank 3x3 Tic Tac Toe board."""
    return [["" for _ in range(3)] for _ in range(3)]


def _check_winner(board: list[list[str]]) -> Optional[str]:
    """Check board for a winner. Returns 'X', 'O' if a player won, or None."""
    lines = []
    lines.extend(board)
    lines.extend([[board[r][c] for r in range(3)] for c in range(3)])
    lines.append([board[i][i] for i in range(3)])
    lines.append([board[i][2 - i] for i in range(3)])
    for line in lines:
        if line[0] and all(cell == line[0] for cell in line):
            return line[0]
    return None


def _is_draw(board: list[list[str]]) -> bool:
    """Check if the board is a draw (all cells filled, no winner)."""
    return (
        all(cell for row in board for cell in row)
        and _check_winner(board) is None
    )


def _next_player(current: str) -> str:
    """Return next player given the current one."""
    return "O" if current == "X" else "X"


def _get_status_and_winner(board: list[list[str]]) -> (str, Optional[str]):
    """
    Returns game status ('ongoing', 'win', 'draw') and winner ('X', 'O', or None).
    """
    winner = _check_winner(board)
    if winner:
        return "win", winner
    if _is_draw(board):
        return "draw", None
    return "ongoing", None


# PUBLIC_INTERFACE
@app.post(
    "/api/game/new",
    response_model=NewGameResponse,
    summary="Start a new Tic Tac Toe game",
    tags=["Game"],
    responses={
        200: {"description": "A new game is started."}
    }
)
def start_new_game():
    """
    Starts a new Tic Tac Toe game and returns the game state and ID.

    Returns:
        - game_id: Unique ID for the game session.
        - board: Initial game board (empty).
        - current_player: 'X' always starts.
        - status: Game status ('ongoing').
        - winner: None.
    """
    game_id = str(uuid.uuid4())
    board = _new_board()
    start_player = "X"
    status, winner = _get_status_and_winner(board)
    games[game_id] = {
        "board": board,
        "current_player": start_player,
        "status": status,
        "winner": winner,
    }
    return NewGameResponse(
        game_id=game_id,
        board=board,
        current_player=start_player,
        status=status,
        winner=winner,
    )


# PUBLIC_INTERFACE
@app.post(
    "/api/game/{game_id}/move",
    response_model=MoveResponse,
    summary="Make a move in a Tic Tac Toe game",
    tags=["Game"],
    responses={
        200: {"description": "Move successful, returns updated game state."},
        404: {"description": "Game not found."},
        409: {"description": "Invalid move (cell taken or game over)."}
    }
)
def make_move(game_id: str, move: MoveRequest):
    """
    Make a move for the current player in the specified game.
    Args:
        - game_id: Unique game session ID.
        - move: The row and column (0-indexed).
    Returns:
        - board: Updated 3x3 board.
        - current_player: Next player, or None if game over.
        - status: 'ongoing', 'win', 'draw'
        - winner: 'X', 'O' or None
    Raises:
        - 404: if game not found
        - 409: if cell is taken, out of bounds, or game already finished
    """
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")
    if game['status'] != "ongoing":
        raise HTTPException(
            status_code=409,
            detail=f"Game already finished with status: {game['status']}"
        )

    row, col = move.row, move.col
    if not (0 <= row <= 2 and 0 <= col <= 2):
        raise HTTPException(
            status_code=409,
            detail="Invalid move: row or column out of range."
        )
    if game['board'][row][col] != "":
        raise HTTPException(
            status_code=409,
            detail="Invalid move: cell already taken."
        )

    game['board'][row][col] = game['current_player']

    status, winner = _get_status_and_winner(game['board'])
    if status == "ongoing":
        next_player = _next_player(game['current_player'])
    else:
        next_player = None

    game.update({
        "current_player": next_player,
        "status": status,
        "winner": winner,
    })

    return MoveResponse(
        board=game['board'],
        current_player=next_player,
        status=status,
        winner=winner,
    )


# PUBLIC_INTERFACE
@app.get(
    "/api/game/{game_id}",
    response_model=GameStateResponse,
    summary="Retrieve current game state",
    tags=["Game"],
    responses={
        200: {"description": "Returns the state of the specified game session."},
        404: {"description": "Game not found."}
    }
)
def get_game_state(game_id: str):
    """
    Get the current board, player, and status of the specified game session.

    Args:
        - game_id: The unique session ID.
    Returns:
        - board: Current 3x3 board
        - current_player: 'X', 'O', or None
        - status: 'ongoing', 'win', or 'draw'
        - winner: 'X', 'O', or None
    Raises:
        - 404: if game not found
    """
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")
    return GameStateResponse(
        game_id=game_id,
        board=game['board'],
        current_player=game['current_player'],
        status=game['status'],
        winner=game['winner'],
    )


# PUBLIC_INTERFACE
@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}
