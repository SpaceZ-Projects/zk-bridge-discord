
import os
import aiohttp
import secrets
import string
import tarfile
import shutil

home = os.path.expanduser("~")

bitcoinz_path = os.path.join(home, ".bitcoinz")
bitcoinz_conf = "bitcoinz.conf"
params_path = os.path.join(home, ".zcash-params")


class Utils():
    def __init__(self):
        super().__init__()
        

    def generate_id(self, length=32):
        alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
        random_bytes = secrets.token_bytes(length)
        address_id = ''.join(alphabet[b % 62] for b in random_bytes)
        return address_id


    def get_config_path(self):
        config_path = os.path.join(bitcoinz_path, bitcoinz_conf)
        if os.path.exists(config_path):
            return config_path
        return None


    def generate_random_string(self, length=16):
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(characters) for _ in range(length))
    

    def get_binary_files(self):
        required_files = [
            'bitcoinzd',
            'bitcoinz-cli',
            'bitcoinz-tx'
        ]
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        return missing_files
    
    
    def get_zk_params(self):
        if not os.path.exists(params_path):
            os.makedirs(params_path)
        required_files = [
            'sprout-proving.key',
            'sprout-verifying.key',
            'sapling-spend.params',
            'sapling-output.params',
            'sprout-groth16.params'
        ]
        missing_files = []
        for file in required_files:
            file_path = os.path.join(params_path, file)
            if not os.path.exists(file_path):
                missing_files.append(file)
        return missing_files
    

    async def fetch_binary_files(self):
        file_name = "bitcoinz-c73d5cdb2b70-x86_64-linux-gnu.tar.gz"
        url = "https://github.com/btcz/bitcoinz/releases/download/2.1.0/"
        destination = os.path.join(file_name)
        self.current_download_file = destination
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + file_name, timeout=None) as response:
                    if response.status == 200:
                        chunk_size = 512
                        self.file_handle = open(destination, 'wb')
                        async for chunk in response.content.iter_chunked(chunk_size):
                            if not chunk:
                                break
                            self.file_handle.write(chunk)
                        self.file_handle.close()
                        self.file_handle = None
                        await session.close()
                        home_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
                        with tarfile.open(destination, 'r:gz') as tar_ref:
                            tar_ref.extractall(home_path)
                        extracted_folder = "bitcoinz-c73d5cdb2b70"
                        bin_folder = os.path.join(extracted_folder, "bin")
                        for exe_file in ["bitcoinzd", "bitcoinz-cli", "bitcoinz-tx"]:
                            src = os.path.join(bin_folder, exe_file)
                            dest = os.path.join(exe_file)
                            if os.path.exists(src):
                                shutil.move(src, dest)
                                os.chmod(dest, 0o755)
                        shutil.rmtree(extracted_folder)
                        os.remove(destination)
        except RuntimeError as e:
            print(f"RuntimeError caught: {e}")
        except aiohttp.ClientError as e:
            print(f"HTTP Error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")


    async def fetch_params_files(self, missing_files):
        base_url = "https://d.btcz.rocks/"
        try:
            async with aiohttp.ClientSession() as session:
                for idx, file_name in enumerate(missing_files):
                    url = base_url + file_name
                    file_path = os.path.join(params_path, file_name)
                    self.current_download_file = file_path
                    async with session.get(url, timeout=None) as response:
                        if response.status == 200:
                            chunk_size = 512
                            self.file_handle = open(file_path, 'wb')
                            async for chunk in response.content.iter_chunked(chunk_size):
                                if not chunk:
                                    break
                                self.file_handle.write(chunk)
                            self.file_handle.close()
                            self.file_handle = None
                    self.current_download_file = None
                await session.close()
        except RuntimeError as e:
            print(f"RuntimeError caught: {e}")
        except aiohttp.ClientError as e:
            print(f"HTTP Error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")


    def create_config_file(self):
        if not os.path.exists(bitcoinz_path):
            os.makedirs(bitcoinz_path)
        config_file_path = os.path.join(bitcoinz_path, bitcoinz_conf)
        try:
            rpcuser = self.generate_random_string(16)
            rpcpassword = self.generate_random_string(32)
            with open(config_file_path, 'w') as config_file:
                config_content = f"""# BitcoinZ configuration file
# Add your configuration settings below

rpcuser={rpcuser}
rpcpassword={rpcpassword}
addnode=178.193.205.17:1989
addnode=51.222.50.26:1989
addnode=146.59.69.245:1989
addnode=37.187.76.80:1989
"""
                config_file.write(config_content)
        except Exception as e:
            print(f"Error creating config file: {e}")