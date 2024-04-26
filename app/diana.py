import asyncio
import threading

from app.tray import Tray
from app.logger import logger
from moonblade import MoonBlade, Router, Node

class Diana(Node):
    def __init__(self) -> None:
        self.LCUx_alive = False
        self.tray = Tray()
        super().__init__()

    def start(self):
        threading.Thread(target=asyncio.run, args=(self.event_loop(), ), daemon=True).start()
        self.tray.start()

    async def stop(self):
        self.tray.stop()
        self.LCUx_alive = False
        await self.mb.stop()

    async def event_loop(self):
        logger.debug('Loop thread created.')
        self.tray.loop = asyncio.get_event_loop()
        
        while True:
            async with MoonBlade() as self.mb:
                await self.mb.start()
                self.LCUx_alive = True
                while self.LCUx_alive:
                    await asyncio.sleep(3)

    @Router.register('/lol-gameflow/v1/gameflow-phase')
    async def on_gameflow_changed(self, data: dict):
        logger.debug('Gameflow changed.', data)

        gamephase = data['data']

        if gamephase is None:
            res = await self.mb.request('get', '/lol-gameflow/v1/gameflow-phase')
            gamephase = await res.json()

        match gamephase:
            case 'ReadyCheck':
                if self.tray.auto_do:
                    await self.mb.request('post', '/lol-matchmaking/v1/ready-check/accept', data={})
            case 'PreEndOfGame':
                if self.tray.skip_ballot:
                    res = await self.mb.request('get', '/lol-honor-v2/v1/ballot')
                    res_json = res.json()
                    data = {'gameId': res_json['gameId'], 'honorCategory': 'OPT_OUT', 'summonerId': 0}
                    await self.mb.request('post', '/lol-honor-v2/v1/honor-player', data=data)
            case 'EndOfGame':
                if self.tray.play_again:
                    await self.mb.request('post', '/lol-lobby/v2/play-again', data={})
            case 'InProgress':
                pass
    
    @Router.register('/lol-lobby/v2/received-invitations')
    async def on_accept_invitation(self, data: dict):
        logger.debug('Received invitations.', data)

        invitations = data['data']
        if invitations is None:
            res = await self.mb.request('get', '/lol-lobby/v2/received-invitations')
            invitations = res.json()

        if self.tray.accept_invitation:
            friends = await self.mb.request('get', '/lol-chat/v1/friends')
            friend_summoner_ids = [i['summonerId'] for i in friends.json()]
            
            invitation_time = 0
            invitation_id = 0
            for invitation in invitations:  # 遍历邀请，接受最新发送的邀请
                if invitation['fromSummonerId'] in friend_summoner_ids and int(invitation['timestamp']) > invitation_time:
                    invitation_id = invitation['invitationId']
            if invitation_id != 0:
                await self.mb.request('post', f'/lol-lobby/v2/received-invitations/{invitation_id}/accept', data={})
        return
    
    @Router.register('/lol-chat/v1/me')
    async def on_chat_event(self, data: dict):
        logger.debug('Chat event.', data)

        data = data['data']
        if data is None:
            res = await self.mb.request('get', '/lol-chat/v1/me')
            data = res.json()

        availability_code = self.tray.availability_code
        availability = ['chat', 'away', 'mobile', 'offline'][availability_code]

        if availability_code == -1:
            return
        
        if data['availability'] != availability:
            data = {'availability': availability}
            await self.mb.request('put', '/lol-chat/v1/me', data=data)
    
    @Router.register('/lol-clash/v1/ready')
    async def on_clash_created(self, data: dict):
        logger.debug('LOL client created.', data)

        is_ready = data['data']
        if is_ready is None:
            res = await self.mb.request('get', '/lol-clash/v1/ready')
            is_ready = res.json()

        if is_ready:
            await self.fold_groups()
            await Router.fake(None, 'Update', '/lol-lobby/v2/received-invitations')

    @Router.register('/riotclient/pre-shutdown/begin')
    async def on_client_shutdown(self, data: dict):
        logger.debug('LOL client closed.', data)
        if self.LCUx_alive:
            self.tray.update('未运行游戏')
            self.tray.notify('已退出英雄联盟，等待重新登录游戏。', '')
            self.LCUx_alive = False
        return
    
    @Router.register('/moonblade/start')
    async def on_start(self, data: dict):
        logger.debug('Diana connected.', data)

        res = await self.mb.request('get', '/lol-chat/v1/me')
        res_json = res.json()
        name = res_json['name']
        self.tray.update('已开始自动操作' if self.tray.auto_do else '已停止自动操作')
        self.tray.notify('已登录英雄联盟。', name)
        await Router.fake(None, 'Update', '/lol-clash/v1/ready')

    async def fold_groups(self):
        logger.debug('Fold groups.')
        groups = await self.mb.request('get', '/lol-chat/v1/friend-groups')
        groups = groups.json()
        for group in groups:
            if not group['collapsed']:
                group['collapsed'] = True
                await self.mb.request('put', f'/lol-chat/v1/friend-groups/{group["id"]}', data=group)
        
        data = {'sortBy': 'availability'}  # 按状态排序
        # data = {'sortBy': 'alphabetical'}  # 按字母顺序排序
        res = await self.mb.request('get', '/lol-chat/v1/settings')
        data = res.json()
        data['sortBy'] = 'availability'
        await self.mb.request('put', '/lol-chat/v1/settings', data=data)

