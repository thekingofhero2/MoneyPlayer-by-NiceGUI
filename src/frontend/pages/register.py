from fastapi import HTTPException
from nicegui import app, ui
from src.models import UserCreate
from src.db.session import get_db_context
from src.repositories.user import user_repo
from src.frontend.components.form_utils import enable_button_on_user_inputs
from src.frontend.components import notifications


@ui.page("/register")
def register_page():
    """Defines the page for user registration."""
    # If already authenticated, redirect to items
    if app.storage.user.get("token"):
        ui.navigate.to("/items")
        return

    with ui.card().classes("absolute-center w-full max-w-md p-8"):
        ui.label("Register").classes("text-h4")

        email = (
            ui.input("Email")
            .props("autocomplete=username outlined")
            .classes("w-full")
        )
        password = (
            ui.input("Password")
            .props("type=password autocomplete=new-password outlined")
            .classes("w-full")
        )
        confirm_password = (
            ui.input("Confirm Password")
            .props("type=password autocomplete=new-password outlined")
            .classes("w-full")
        )
        register_button = (
            ui.button("Register").props("color=primary").classes("w-full")
        )

        register_button.on("click", lambda: perform_register(email, password, confirm_password))
        email.on("keydown.enter", lambda: perform_register(email, password, confirm_password))
        password.on("keydown.enter", lambda: perform_register(email, password, confirm_password))
        confirm_password.on("keydown.enter", lambda: perform_register(email, password, confirm_password))

        email.on(
            "update:model-value",
            lambda: enable_button_on_user_inputs([email, password, confirm_password], register_button),
        )
        password.on(
            "update:model-value",
            lambda: enable_button_on_user_inputs([email, password, confirm_password], register_button),
        )
        confirm_password.on(
            "update:model-value",
            lambda: enable_button_on_user_inputs([email, password, confirm_password], register_button),
        )

        # Set the initial disabled state of the button
        enable_button_on_user_inputs([email, password, confirm_password], register_button)

        # Add link to login page
        with ui.row().classes("w-full justify-center mt-4"):
            ui.label("Already have an account?")
            ui.html('<a href="/login" style="color: #1976d2; text-decoration: none;">Log in</a>', sanitize=False)


async def perform_register(
    email_input: ui.input,
    password_input: ui.input,
    confirm_password_input: ui.input
):
    """Registers a new user using data from the input elements."""
    # Validate inputs
    if not email_input.validate() or not password_input.validate() or not confirm_password_input.validate():
        return

    # Check if passwords match
    if password_input.value != confirm_password_input.value:
        notifications.show_error("Passwords do not match")
        return

    # Check password length
    if len(password_input.value) < 8:
        notifications.show_error("Password must be at least 8 characters long")
        return

    try:
        with get_db_context() as db:
            user_in = UserCreate(
                email=email_input.value,
                password=password_input.value,
                is_superuser=False,  # Regular users are not superusers by default
            )
            user = user_repo.register(db=db, obj_in=user_in)

        notifications.show_success(f"User '{email_input.value}' registered successfully!")
        
        # Clear form
        email_input.value = ""
        password_input.value = ""
        confirm_password_input.value = ""
        
        # Redirect to login page
        ui.navigate.to("/login")
        
    except HTTPException as e:
        notifications.show_error(e.detail)
    except Exception as e:
        notifications.show_error(f"An unexpected error occurred: {e}")
