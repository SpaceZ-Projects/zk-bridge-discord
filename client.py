
import os
import asyncio
import subprocess
import json
import binascii

client_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitcoinz-cli")

class Client():
    def __init__(self):
        super().__init__()

    async def execute_bitcoinz_node(self):
        command = ["./bitcoinzd", "-daemon"]
        self.process = None
        try:
            self.process = await asyncio.create_subprocess_exec(
                    *command,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE
            )
        except Exception as e:
            print(e)
        finally:
            if self.process:
                await self.process.wait()
                self.process = None


    async def _run_command(self, command):
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                if stdout:
                    try:
                        data = json.loads(stdout.decode())
                        result = json.dumps(data, indent=4)
                        return result, None
                    except json.JSONDecodeError:
                        return stdout.decode().strip(), None
                else:
                    return None, None
            else:
                error_message = stderr.decode()
                if "error message:" in error_message:
                    index = error_message.index("error message:")+len("error message:")
                    return None, error_message[index:].strip()
                else:
                    return None, None
        except Exception as e:
            print(f"An error occurred while running command {command}: {e}")
            return None, None
        
    
    async def getInfo(self):
        command = f'{client_file} getinfo'
        return await self._run_command(command)
    
    async def getBlockchainInfo(self):
        command = f'{client_file} getblockchaininfo'
        return await self._run_command(command)
    
    async def z_getNewAddress(self):
        command = f'{client_file} z_getnewaddress'
        return await self._run_command(command)
    
    async def z_getBalance(self, address):
        command = f'{client_file} z_getbalance "{address}"'
        return await self._run_command(command)
    
    async def z_ExportKey(self, address):
        command = f'{client_file} z_exportkey "{address}"'
        return await self._run_command(command)
    
    async def z_listUnspent(self, address):
        command = f'{client_file} z_listunspent 0 9999999 true "[\\"{address}\\"]"'
        return await self._run_command(command)
    
    async def SendMemo(self, uaddress, toaddress, amount, txfee, memo):
        hex_memo = binascii.hexlify(memo.encode()).decode()
        command = f'{client_file} z_sendmany "{uaddress}" "[{{\\"address\\": \\"{toaddress}\\", \\"amount\\": {amount}, \\"memo\\": \\"{hex_memo}\\"}}]" 1 {txfee}'
        return await self._run_command(command)
    
    async def SendMemoToMany(self, uaddress, addresses):
        transactions_json = json.dumps(addresses)
        addresses_array = transactions_json.replace('"', '\\"')
        command = f'{client_file} z_sendmany "{uaddress}" "{addresses_array}" 1 0.0001'
        return await self._run_command(command)
    
    async def z_getOperationStatus(self, operation_ids):
        command = f'{client_file} z_getoperationstatus "[\\"{operation_ids}\\"]"'
        return await self._run_command(command)
    
    async def z_getOperationResult(self, operation_ids):
        command = f'{client_file} z_getoperationresult "[\\"{operation_ids}\\"]"'
        return await self._run_command(command)
    
    async def z_ImportKey(self, key):
        command = f'{client_file} z_importkey "{key}" yes'
        return await self._run_command(command)