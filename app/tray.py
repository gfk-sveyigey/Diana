import asyncio

import pystray
import keyboard

from app.icon import Icon
from app.logger import logger
from moonblade import Router

class Tray:
    auto_do = True
    skip_ballot = True
    play_again = True
    accept_invitation = True
    auto_apply_settings = False
    availability_code = -1
    loop = None
    def __init__(self) -> None:
        # tray
        menu = pystray.Menu(
            pystray.MenuItem('自动接受\tF10', self.auto_accept_switch, lambda _: self.auto_do),
            pystray.MenuItem('游戏状态', pystray.Menu(
                pystray.MenuItem('在线', self.availability_switch(0), lambda _: self.availability_code == 0),
                pystray.MenuItem('离开', self.availability_switch(1), lambda _: self.availability_code == 1),
                pystray.MenuItem('移动在线', self.availability_switch(2), lambda _: self.availability_code == 2),
                pystray.MenuItem('离线', self.availability_switch(3), lambda _: self.availability_code == 3),
            )),
            pystray.MenuItem('游戏设置', pystray.Menu(
                pystray.MenuItem('保存设置', None, enabled=False),
                pystray.MenuItem('应用设置', None, enabled=False),
                pystray.MenuItem('自动应用', None, enabled=False),
            )),
            pystray.MenuItem('其它设置', pystray.Menu(
                pystray.MenuItem(
                    text='跳过点赞',
                    action=lambda _: self.skip_ballot_switch,
                    checked=lambda _: self.skip_ballot
                ),
                pystray.MenuItem(
                    text='跳过结算',
                    action=lambda _: self.play_again_switch,
                    checked=lambda _: self.play_again
                ),
                pystray.MenuItem(
                    text='接受邀请',
                    action=lambda _: self.accept_invitation_switch,
                    checked=lambda _: self.accept_invitation
                ),
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('退出\tF11', lambda: self.stop())
        )

        self.tray = pystray.Icon(
            name='Diana',
            icon=Icon().custom(),
            title='未运行游戏',
            menu=menu
        )
        logger.info('Tray created.')

        # hotkey
        keyboard.add_hotkey('f10', self.auto_accept_switch, args=(None, None))
        keyboard.add_hotkey('f11', self.stop, suppress=True)
        logger.info('Hotkey added.')

        return

    def start(self):
        self.tray.run()
        logger.debug('Show tray.')

    def stop(self):
        self.tray.stop()
        logger.debug('Close tray.')
        return

    def update(self, title:str):
        self.tray.title = title
        self.tray.update_menu()
        logger.debug('Flash tray.')
        return
    
    def notify(self, message:str, title:str):
        self.tray.notify(message, title)
        return

    def auto_accept_switch(self, icon, item):
        self.auto_do = not self.auto_do
        self.title = '已开始自动操作' if self.auto_do else '已停止自动操作'
        self.tray.title = self.title
        self.tray.update_menu()
        return

    def availability_switch(self, index):
        def inner(icon, item):
            self.availability_code = (-1 if self.availability_code == index else index)
            if self.availability_code != -1 and self.loop is not None:
                asyncio.run_coroutine_threadsafe(Router.fake(None, 'Update', '/lol-chat/v1/me'), self.loop)
                logger.debug('Change game status.')
        return inner

    def skip_ballot_switch(self, icon, item):
        self.skip_ballot = not self.skip_ballot

    def play_again_switch(self, icon, item):
        self.play_again = not self.play_again

    def accept_invitation_switch(self, icon, item):
        self.accept_invitation = not self.accept_invitation


