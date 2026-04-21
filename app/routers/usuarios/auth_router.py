from html import escape

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user
from app.schemas.usuarios.usuarios_schema import (
    LoginSchema,
    TokenResponse,
    ResetPasswordSchema,
    ResultMessageResponse,
    CreateClientResponse,
    ClientAssignmentResponse,
    TallerInvitationCreateSchema,
    TallerInvitationCreateResponse,
)
from app.repositories.usuarios_repository import get_user_by_email
from app.models.usuarios.usuario import User
from app.services.usuarios_service import (
    reset_user_password,
    create_client_for_current_user,
    check_current_user_is_client,
    send_taller_invitation,
    accept_taller_invitation,
)

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


def _invitation_response_page(
    *,
    title: str,
    message: str,
    is_success: bool,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    eyebrow = "Todo listo" if is_success else "No se pudo completar"
    status_class = "success" if is_success else "error"
    safe_title = escape(title)
    safe_message = escape(message)

    html = f"""
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{safe_title}</title>
        <style>
            :root {{
                color-scheme: light;
                --color-fondo: #e4ecf3;
                --color-tarjeta: #ffffff;
                --color-hover-suave: #e8edf2;
                --color-texto: #111827;
                --color-texto-secundario: #4b5563;
                --color-titulo: #0b1f4d;
                --color-borde: #d1d5db;
                --color-boton-navbar: #fc3b01;
                --color-error: #dc2626;
                --color-error-fondo: #fef2f2;
            }}

            * {{
                box-sizing: border-box;
            }}

            body {{
                min-height: 100vh;
                margin: 0;
                display: grid;
                place-items: center;
                padding: 24px;
                font-family: Arial, Helvetica, sans-serif;
                background:
                    linear-gradient(135deg, rgba(11, 31, 77, 0.14), transparent 34%),
                    linear-gradient(315deg, rgba(252, 59, 1, 0.12), transparent 30%),
                    var(--color-fondo);
                color: var(--color-texto);
            }}

            main {{
                width: min(100%, 520px);
                padding: 36px;
                border: 1px solid var(--color-borde);
                border-radius: 8px;
                background: var(--color-tarjeta);
                box-shadow: 0 22px 55px rgba(11, 31, 77, 0.16);
                text-align: center;
            }}

            .mark {{
                width: 76px;
                height: 76px;
                margin: 0 auto 24px;
                display: grid;
                place-items: center;
                border-radius: 50%;
                background: var(--color-hover-suave);
                color: var(--color-titulo);
            }}

            .mark.error {{
                background: var(--color-error-fondo);
                color: var(--color-error);
            }}

            .mark::before {{
                content: "";
                width: 30px;
                height: 16px;
                border-left: 5px solid currentColor;
                border-bottom: 5px solid currentColor;
                transform: rotate(-45deg) translate(2px, -2px);
            }}

            .mark.error::before {{
                content: "!";
                width: auto;
                height: auto;
                border: 0;
                transform: none;
                font-size: 38px;
                font-weight: 700;
                line-height: 1;
            }}

            .eyebrow {{
                margin: 0 0 10px;
                color: {"var(--color-titulo)" if is_success else "var(--color-error)"};
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0;
                text-transform: uppercase;
            }}

            h1 {{
                margin: 0;
                color: var(--color-titulo);
                font-size: 34px;
                line-height: 1.15;
            }}

            p {{
                margin: 18px 0 0;
                color: var(--color-texto-secundario);
                font-size: 17px;
                line-height: 1.6;
            }}

            .footer {{
                margin-top: 28px;
                padding-top: 20px;
                border-top: 1px solid var(--color-borde);
                color: var(--color-texto-secundario);
                font-size: 14px;
            }}

            @media (max-width: 520px) {{
                main {{
                    padding: 28px 20px;
                }}

                h1 {{
                    font-size: 28px;
                }}
            }}
        </style>
    </head>
    <body>
        <main>
            <div class="mark {status_class}" aria-hidden="true"></div>
            <p class="eyebrow">{eyebrow}</p>
            <h1>{safe_title}</h1>
            <p>{safe_message}</p>
            <div class="footer">Ya puedes cerrar esta ventana y continuar usando AMI.</div>
        </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=status_code)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(credentials: LoginSchema, db: Session = Depends(get_db)):
    """
    Endpoint de login que valida email y contrasena, devuelve un token JWT.
    """
    usuario = get_user_by_email(db, credentials.email)
    
    if not usuario or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrecta",
        )
    
    if not verify_password(credentials.contrasena, usuario.contrasena):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrecta",
        )
    
    access_token = create_access_token(usuario.id_usuario, usuario.email)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=dict, status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Endpoint protegido que devuelve los datos del usuario actual (desde el token JWT).
    
    Requiere: Authorization: Bearer <token>
    """
    return {
        "id_usuario": current_user.id_usuario,
        "email": current_user.email,
        "activo": current_user.activo,
        "persona": {
            "id_persona": current_user.persona.id_persona,
            "nombre_completo": current_user.persona.nombre_completo,
            "fecha_nacimiento": current_user.persona.fecha_nacimiento,
            "genero": current_user.persona.genero,
            "telefono": current_user.persona.telefono,
            "documento": current_user.persona.documento,
        }
    }


@router.post("/reset-password", response_model=ResultMessageResponse, status_code=status.HTTP_200_OK)
def reset_password(payload: ResetPasswordSchema, db: Session = Depends(get_db)):
    return reset_user_password(db, payload.email)


@router.post("/create-client", response_model=CreateClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Asigna el rol CLIENTE (id_rol=3) al usuario autenticado y crea su registro en cliente.

    Requiere: Authorization: Bearer <token>
    """
    return create_client_for_current_user(db, current_user)


@router.get("/is-client", response_model=ClientAssignmentResponse, status_code=status.HTTP_200_OK)
def is_client(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verifica si el usuario autenticado tiene un registro en la tabla cliente.

    Requiere: Authorization: Bearer <token>
    """
    return check_current_user_is_client(db, current_user)


@router.post(
    "/talleres/invitaciones",
    response_model=TallerInvitationCreateResponse,
    status_code=status.HTTP_200_OK,
)
def create_taller_invitation(
    payload: TallerInvitationCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envia una invitacion por correo para que un usuario sea proveedor de un taller."""
    return send_taller_invitation(db, current_user, payload.email, payload.id_taller)


@router.get(
    "/talleres/invitaciones/aceptar",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
)
def accept_invitation(token: str | None = None, db: Session = Depends(get_db)):
    """Acepta una invitacion de taller usando el token recibido por correo."""
    if not token:
        return _invitation_response_page(
            title="Invitacion no valida",
            message="El enlace de invitacion no incluye un token valido. Solicita una nueva invitacion al taller.",
            is_success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = accept_taller_invitation(db, token)
    except HTTPException as exc:
        return _invitation_response_page(
            title="Invitacion no valida",
            message=str(exc.detail),
            is_success=False,
            status_code=exc.status_code,
        )

    return _invitation_response_page(
        title="Invitacion aceptada",
        message=result["message"],
        is_success=True,
    )
