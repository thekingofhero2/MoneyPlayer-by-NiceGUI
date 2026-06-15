from fastapi import HTTPException
from nicegui import app, ui
from src.models.models import UserCreate
from src.db.session import get_db_context
from src.repositories.user import user_repo
from src.core.security import verify_password, get_password_hash
from src.frontend.layouts.default import dashboard_frame
from src.frontend.components.auth_utils import get_current_user_from_state
from src.frontend.components.form_utils import enable_button_on_user_inputs
from src.frontend.components import notifications
import os
from pathlib import Path


@ui.page("/profile")
def profile_page():
    """Defines the user profile/center page."""
    with dashboard_frame(title="个人中心"):
        # Get current user
        with get_db_context() as db:
            try:
                current_user = get_current_user_from_state(db)
            except Exception:
                ui.navigate.to("/login")
                return

        # Create tabs for different sections
        with ui.tabs().classes('w-full') as tabs:
            profile_tab = ui.tab('基本信息')
            password_tab = ui.tab('修改密码')
            avatar_tab = ui.tab('头像设置')

        with ui.tab_panels(tabs, value=profile_tab).classes('w-full max-w-2xl mt-4'):
            # Profile Tab - Basic Information
            with ui.tab_panel(profile_tab):
                with ui.card().classes('w-full p-6'):
                    ui.label('基本信息').classes('text-h5 mb-4')
                    
                    # Display current user info
                    email_input = ui.input('邮箱', value=current_user.email)
                    email_input.props('outlined disable').classes('w-full')  # Email cannot be changed
                    
                    full_name_input = ui.input('姓名', value=current_user.full_name or '')
                    full_name_input.props('outlined').classes('w-full')
                    
                    # User ID and status display
                    with ui.row().classes('w-full mt-2'):
                        ui.label(f'用户 ID: {current_user.id}').classes('text-gray-600')
                    
                    with ui.row().classes('w-full'):
                        status_text = '已激活' if current_user.is_active else '未激活'
                        ui.label(f'状态：{status_text}').classes('text-gray-600')
                    
                    save_profile_btn = (
                        ui.button('保存', icon='save')
                        .props('color=primary')
                        .classes('mt-4')
                    )
                    
                    save_profile_btn.on(
                        'click',
                        lambda: update_profile(full_name_input)
                    )

            # Password Tab - Change Password
            with ui.tab_panel(password_tab):
                with ui.card().classes('w-full p-6'):
                    ui.label('修改密码').classes('text-h5 mb-4')
                    
                    current_password = (
                        ui.input('当前密码')
                        .props('type=password outlined')
                        .classes('w-full')
                    )
                    
                    new_password = (
                        ui.input('新密码')
                        .props('type=password outlined')
                        .classes('w-full')
                    )
                    
                    confirm_password = (
                        ui.input('确认新密码')
                        .props('type=password outlined')
                        .classes('w-full')
                    )
                    
                    change_password_btn = (
                        ui.button('修改密码', icon='lock_reset')
                        .props('color=primary')
                        .classes('mt-4')
                    )
                    
                    # Enable button when all fields are filled
                    for input_field in [current_password, new_password, confirm_password]:
                        input_field.on(
                            'update:model-value',
                            lambda: enable_button_on_user_inputs(
                                [current_password, new_password, confirm_password],
                                change_password_btn
                            )
                        )
                    
                    enable_button_on_user_inputs(
                        [current_password, new_password, confirm_password],
                        change_password_btn
                    )
                    
                    change_password_btn.on(
                        'click',
                        lambda: perform_change_password(
                            current_password, new_password, confirm_password
                        )
                    )

            # Avatar Tab - Avatar Settings
            with ui.tab_panel(avatar_tab):
                with ui.card().classes('w-full p-6'):
                    ui.label('头像设置').classes('text-h5 mb-4')
                    
                    # Create avatar directory if not exists
                    avatar_dir = Path('images/avatars')
                    avatar_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Avatar display
                    avatar_path = f'images/avatars/user_{current_user.id}.jpg'
                    default_avatar = 'https://ui-avatars.com/api/?name=' + (current_user.full_name or current_user.email.split('@')[0])
                    
                    with ui.row().classes('w-full justify-center mb-4'):
                        avatar_image = ui.image(default_avatar).classes('w-32 h-32 rounded-full')
                    
                    # Avatar upload
                    with ui.row().classes('w-full justify-center'):
                        async def upload_avatar(e):
                            try:
                                # Save uploaded file using e.file.save()
                                upload_path = avatar_dir / f'user_{current_user.id}.jpg'
                                await e.file.save(str(upload_path))
                                
                                # Update image with timestamp to force refresh
                                import time
                                avatar_image.set_source(f'{avatar_path}?t={int(time.time())}')
                                notifications.show_success('头像上传成功！')
                            except Exception as ex:
                                notifications.show_error(f'上传失败：{str(ex)}')
                        
                        uploader = ui.upload(
                            label='上传头像',
                            on_upload=upload_avatar
                        ).props('outlined accept="image/*"').classes('w-full max-w-xs')
                    
                    # Avatar reset button
                    with ui.row().classes('w-full justify-center mt-4'):
                        reset_avatar_btn = (
                            ui.button('使用默认头像', icon='refresh')
                            .props('color=secondary outline')
                        )
                        reset_avatar_btn.on('click', lambda: avatar_image.set_source(default_avatar))

        # Logout button at bottom
        with ui.row().classes('w-full justify-center mt-8'):
            logout_btn = (
                ui.button('退出登录', icon='logout', color='negative')
                .props('flat')
            )
            
            async def handle_logout():
                from src.frontend.state import clear_auth
                clear_auth()
                app.storage.user.clear()
                ui.navigate.to('/login')
            
            logout_btn.on('click', handle_logout)


async def update_profile(full_name_input: ui.input):
    """Update user profile information."""
    with get_db_context() as db:
        try:
            current_user = get_current_user_from_state(db)
            
            # Update full name
            if full_name_input.value != current_user.full_name:
                current_user.full_name = full_name_input.value if full_name_input.value else None
                db.add(current_user)
                db.commit()
                db.refresh(current_user)
            
            notifications.show_success('个人信息更新成功！')
            
        except HTTPException as e:
            notifications.show_error(e.detail)
        except Exception as e:
            notifications.show_error(f'更新失败：{str(e)}')


async def perform_change_password(
    current_password_input: ui.input,
    new_password_input: ui.input,
    confirm_password_input: ui.input
):
    """Change user password."""
    # Validate inputs
    if not current_password_input.validate() or not new_password_input.validate() or not confirm_password_input.validate():
        return
    
    # Check if passwords match
    if new_password_input.value != confirm_password_input.value:
        notifications.show_error('新密码和确认密码不一致')
        return
    
    # Check password length
    if len(new_password_input.value) < 8:
        notifications.show_error('密码长度至少为 8 位')
        return
    
    with get_db_context() as db:
        try:
            current_user = get_current_user_from_state(db)
            
            # Verify current password
            if not verify_password(current_password_input.value, current_user.hashed_password):
                notifications.show_error('当前密码错误')
                return
            
            # Update password
            current_user.hashed_password = get_password_hash(new_password_input.value)
            db.add(current_user)
            db.commit()
            
            # Clear inputs
            current_password_input.value = ''
            new_password_input.value = ''
            confirm_password_input.value = ''
            
            notifications.show_success('密码修改成功！')
            
        except HTTPException as e:
            notifications.show_error(e.detail)
        except Exception as e:
            notifications.show_error(f'修改失败：{str(e)}')
