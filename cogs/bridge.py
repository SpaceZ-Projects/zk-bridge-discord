
import asyncio
import binascii
import json
import re

from discord.app_commands import Group
from discord import (
    Embed, Interaction, Permissions, NotFound,
    HTTPException, Forbidden, Colour, Message
)
from discord.ext import commands, tasks

from utils import Utils
from storage import Storage
from client import Client


class Bridge(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

        self.utils = Utils()
        self.storage = Storage()
        self.commands = Client()

        self.is_running = None
        self.addresses_list = []
        self.processed_timestamps = set()

    bridge = Group(name="bridge", description="Admin Commands", default_permissions=Permissions(administrator=True), guild_only=True)


    @bridge.command(name="start", description="start the bridge")
    async def bridge_start(self, ctx:Interaction):
        await ctx.response.defer(ephemeral=True)
        embed = self.embed("Starting Bridge","Status :", "Verify node status...")
        await ctx.followup.send(embed=embed)
        identity = self.storage.get_identity()
        if not identity:
            embed = self.embed("Starting Bridge","Error :", "Setup a bridge channel first")
            await ctx.edit_original_response(embed=embed)
            return
        elif self.is_running:
            embed = self.embed("Starting Bridge","Error :", "Bridge is already running.")
            await ctx.edit_original_response(embed=embed)
            return
        result, error= await self.commands.getInfo()
        if error is not None:
            embed = self.embed("Starting Bridge","Error :", error)
            await ctx.edit_original_response(embed=embed)
            return
        if result:
            blockchaininfo, _ = await self.commands.getBlockchainInfo()
            if isinstance(blockchaininfo, str):
                info = json.loads(blockchaininfo)
            if info is not None:
                sync = info.get('verificationprogress')
                sync_percentage = sync * 100
                if sync_percentage > 99.95:
                    await self.gather_new_memos()
                    embed = self.embed("Starting Bridge","Status :", "Bridge is running.")
                    await ctx.edit_original_response(embed=embed)
                    self.is_running = True
            else:
                embed = self.embed("Starting Bridge","Status :", "Node is not fully sync...")
                await ctx.edit_original_response(embed=embed)
        else:
            embed = self.embed("Starting Bridge","Error :", "Node is not running.")
            await ctx.edit_original_response(embed=embed)


    async def gather_new_memos(self):
        address = self.storage.get_identity("address")
        if address:
            listunspent,_= await self.commands.z_listUnspent(address[0])
            if listunspent:
                listunspent = json.loads(listunspent)
                list_txs = self.storage.get_txs()
                for data in listunspent:
                    txid = data['txid']
                    if txid not in list_txs:
                        await self.unhexlify_memo(data)

                self.waiting_new_memos.start()
                self.manage_contacts.start()
                self.manage_messages.start()
                

    @tasks.loop(seconds=5)
    async def waiting_new_memos(self):
        address = self.storage.get_identity("address")
        if address:
            listunspent,_= await self.commands.z_listUnspent(address[0])
            if listunspent:
                listunspent = json.loads(listunspent)
                if len(listunspent) >= 25:
                    total_balance,_ = await self.commands.z_getBalance(address[0])
                    txfee = 0.0001
                    amount = float(total_balance) - txfee
                    await self.merge_utxos(address[0], amount, txfee)
                list_txs = self.storage.get_txs()
                for utxo in listunspent:
                    txid = utxo['txid']
                    if txid not in list_txs:
                        await self.unhexlify_memo(utxo)


    async def merge_utxos(self, address, amount, txfee):
        memo = "merge"
        operation, _= await self.commands.SendMemo(address, address, amount, txfee, memo)
        if operation:
            transaction_status, _= await self.commands.z_getOperationStatus(operation)
            transaction_status = json.loads(transaction_status)
            if isinstance(transaction_status, list) and transaction_status:
                status = transaction_status[0].get('status')
                if status == "executing" or status =="success":
                    await asyncio.sleep(1)
                    while True:
                        transaction_result, _= await self.commands.z_getOperationResult(operation)
                        transaction_result = json.loads(transaction_result)
                        if isinstance(transaction_result, list) and transaction_result:
                            status = transaction_result[0].get('status')
                            result = transaction_result[0].get('result', {})
                            if status == "failed":
                                    return
                            txid = result.get('txid')
                            self.storage.tx(txid)
                            return
                        await asyncio.sleep(2)

    
    async def unhexlify_memo(self, utxo):
        memo = utxo['memo']
        amount = utxo['amount']
        txid = utxo['txid']
        try:
            decoded_memo = binascii.unhexlify(memo)
            form = decoded_memo.decode('utf-8')
            clean_form = form.rstrip('\x00')
            form_dict = json.loads(clean_form)
            form_type = form_dict.get('type')

            if form_type == "message":
                await self.get_message(form_dict, amount)
                self.storage.tx(txid)
            elif form_type == "request":
                await self.get_request(form_dict)
                self.storage.tx(txid)

        except (binascii.Error, json.decoder.JSONDecodeError) as e:
            self.storage.tx(txid)
            print(f"Received new transaction. Amount: {amount}")
        except Exception as e:
            self.storage.tx(txid)
            print(f"Received new transaction. Amount: {amount}")


    async def get_message(self, form, amount):
        contact_id = form.get('id')
        author = form.get('username')
        message = form.get('text')
        timestamp = await self.get_message_timestamp()
        contact_username = self.storage.get_contact_username(contact_id)
        if not contact_username:
            return
        self.processed_timestamps.add(timestamp)
        if author != contact_username:
            self.storage.update_contact_username(author, contact_id)
        redirect_message = await self.redirect_message_to_channel(author, message, amount)
        if redirect_message:
            self.storage.message(contact_id, author, message, amount, redirect_message, timestamp)

    
    async def get_request(self, form):
        category = form.get('category')
        contact_id = form.get('id')
        username = form.get('username')
        address = form.get('address')
        banned = self.storage.get_banned()
        if address in banned:
            return
        self.storage.add_pending(category, contact_id, username, address)


    async def redirect_message_to_channel(self, author, new_message, amount):
        channel_id = self.storage.get_identity("channel")
        if channel_id:
            try:
                chat = self.client.get_channel(channel_id[0])
                message_form = f"**{author} :** {new_message}"
                if amount > 0.0001:
                    gift = float(amount) - 0.0001
                    message_form += f"\n:gift:__Gift :__ {gift}"
                message = await chat.send(message_form)
                return message.id
            except NotFound:
                print("Error: The channel was not found.")
            except Forbidden:
                print("Error: The bot does not have permission to send a message.")
            except HTTPException as e:
                print(f"HTTP error occurred: {e}")


    @tasks.loop(seconds=5)
    async def manage_contacts(self):
        pending_list = self.storage.get_pending()
        if pending_list:
            for contact in pending_list:
                category = contact[0]
                contact_id = contact[1]
                username = contact[2]
                address = contact[3]

                await self.send_identity(category, contact_id, username, address)


    async def send_identity(self, category, contact_id, username, toaddress):
        amount = 0.0001
        txfee = 0.0001
        group_category, group_username, group_address = self.storage.get_identity()
        group_id = self.utils.generate_id()
        memo = {"type":"identity","category":group_category,"id":group_id,"username":group_username,"address":group_address}
        memo_str = json.dumps(memo)
        await self.send_identity_memo(
            category,
            contact_id,
            username,
            group_id,
            group_address,
            toaddress,
            amount,
            txfee,
            memo_str
        )


    async def send_identity_memo(self, category, contact_id, username, group_id, group_address, toaddress, amount, txfee, memo):
        operation, _= await self.commands.SendMemo(group_address, toaddress, amount, txfee, memo)
        if operation:
            transaction_status, _= await self.commands.z_getOperationStatus(operation)
            transaction_status = json.loads(transaction_status)
            if isinstance(transaction_status, list) and transaction_status:
                status = transaction_status[0].get('status')
                if status == "executing" or status =="success":
                    await asyncio.sleep(1)
                    while True:
                        transaction_result, _= await self.commands.z_getOperationResult(operation)
                        transaction_result = json.loads(transaction_result)
                        if isinstance(transaction_result, list) and transaction_result:
                            status = transaction_result[0].get('status')
                            result = transaction_result[0].get('result', {})
                            if status == "failed":
                                    return
                            txid = result.get('txid')
                            self.storage.tx(txid)
                            self.storage.delete_pending(toaddress)
                            self.storage.add_contact(category, group_id, contact_id, username, toaddress)
                            await self.send_note_to_channel(username)
                            return
                        await asyncio.sleep(2)


    async def send_note_to_channel(self, usename):
        channel_id = self.storage.get_identity("channel")
        try:
            embed = self.embed("New User",usename, "**Welcome to ZKGroup**")
            chat = self.client.get_channel(channel_id[0])
            await chat.send(embed=embed)
        except NotFound:
            print("Error: The channel was not found.")
        except Forbidden:
            print("Error: The bot does not have permission to send a message.")
        except HTTPException as e:
            print(f"HTTP error occurred: {e}")


    
    @tasks.loop(seconds=5)
    async def manage_messages(self):
        messages_list = self.storage.get_messages()
        contacts_list = self.storage.get_contacts()     
        if messages_list:
            messages_list.sort(key=lambda x: x[5])
            for data in messages_list:
                id = data[0]
                author= data[1]
                message= data[2]
                message_id= data[4]
                for contact_data in contacts_list:
                    group_id = contact_data[1]
                    contact_id = contact_data[2]
                    address = contact_data[4]
                    if id != contact_id:
                        self.addresses_list.append((group_id, address))
                await self.send_message_memo(message, author, message_id)
                self.addresses_list = []



    async def send_message_memo(self, message, author, message_id):
        amount = 0.0001
        chunk_size = 54
        _, group_username, group_address = self.storage.get_identity()
        address_chunks = [self.addresses_list[i:i + chunk_size] for i in range(0, len(self.addresses_list), chunk_size)]
        for chunk in address_chunks:
            timestamp = await self.get_message_timestamp()
            transactions = []
            for group_id, address in chunk:
                memo = {
                    "type": "message",
                    "id": group_id,
                    "username":group_username,
                    "text": f"{author} : {message}",
                    "timestamp":timestamp
                }
                memo_str = json.dumps(memo)
                hex_memo = binascii.hexlify(memo_str.encode()).decode()
                transactions.append({
                    "address": address,
                    "amount": amount,
                    "memo": hex_memo
                })
            operation, _ = await self.commands.SendMemoToMany(group_address, transactions)
            if operation:
                transaction_status, _ = await self.commands.z_getOperationStatus(operation)
                transaction_status = json.loads(transaction_status)
                if isinstance(transaction_status, list) and transaction_status:
                    status = transaction_status[0].get('status')
                    if status == "executing" or status == "success":
                        await asyncio.sleep(1)
                        while True:
                            transaction_result, _ = await self.commands.z_getOperationResult(operation)
                            transaction_result = json.loads(transaction_result)
                            if isinstance(transaction_result, list) and transaction_result:
                                status = transaction_result[0].get('status')
                                result = transaction_result[0].get('result', {})
                                print(result)
                                if status == "failed":
                                    return
                                txid = result.get('txid')
                                self.storage.tx(txid)
                                self.storage.delete_message(message_id)
                                return
                            await asyncio.sleep(2)



    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.guild:
            if message.author.id == self.client.user.id:
                return
            
            amount = 0.0001
            channel_id = self.storage.get_identity("channel")
            
            if channel_id:
                if message.channel.id == channel_id[0]:
                    message_content = message.content
                    has_attachment = message.attachments and any(attachment.width and attachment.height for attachment in message.attachments)
                    media_links = []
                    if has_attachment:
                        for attachment in message.attachments:
                            media_links.append(attachment.url)
                    
                    if media_links:
                        message_content += " " + " ".join(media_links)
                    
                    cleaned_content = re.sub(r'[*>_<-]', '', message_content)
                    
                    if len(cleaned_content) > 325:
                        words = cleaned_content.split()
                        chunk = ""
                        chunks = []
                        for word in words:
                            if len(chunk) + len(word) + 1 <= 325:
                                chunk += " " + word if chunk else word
                            else:
                                chunks.append(chunk)
                                chunk = word
                        if chunk:
                            chunks.append(chunk)
                        
                        for chunk in chunks:
                            timestamp = await self.get_message_timestamp()
                            self.storage.message(
                                message.author.id,
                                message.author.display_name,
                                chunk,
                                amount,
                                message.id,
                                timestamp
                            )
                    else:
                        timestamp = await self.get_message_timestamp()
                        self.storage.message(
                            message.author.id,
                            message.author.display_name,
                            cleaned_content,
                            amount,
                            message.id,
                            timestamp
                        )


    async def get_message_timestamp(self):
        blockchaininfo, _ = await self.commands.getBlockchainInfo()
        if blockchaininfo is not None:
            if isinstance(blockchaininfo, str):
                info = json.loads(blockchaininfo)
                if info is not None:
                    timestamp = info.get('mediantime')
                    if timestamp in self.processed_timestamps:
                        highest_timestamp = max(self.processed_timestamps)
                        timestamp = highest_timestamp + 1
                    self.processed_timestamps.add(timestamp)
                    return timestamp


    def embed(self, title, field_name, field_value):
        embed = Embed()
        embed.title = title
        embed.color = Colour(0x2b2d31)
        embed.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
        return embed


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Bridge(client))