from django.shortcuts import render
from django.template import RequestContext
from django.contrib import messages
from django.http import HttpResponse
import datetime
import ipfshttpclient
import os
import json
from web3 import Web3, HTTPProvider
from django.core.files.storage import FileSystemStorage
import pickle
from ecies.utils import generate_eth_key, generate_key
from ecies import encrypt, decrypt
from hashlib import sha256
import boto3

api = ipfshttpclient.Client(host='http://127.0.0.1', port=5001)
global details, username

#function to generate public and private keys for ECC algorithm
def ECCGenerateKeys():
    if os.path.exists("pvt.key"):
        with open("pvt.key", 'rb') as f:
            private_key = f.read()
        f.close()
        with open("pri.key", 'rb') as f:
            public_key = f.read()
        f.close()
        private_key = private_key.decode()
        public_key = public_key.decode()
    else:
        secret_key = generate_eth_key()
        private_key = secret_key.to_hex()  # hex string
        public_key = secret_key.public_key.to_hex()
        with open("pvt.key", 'wb') as f:
            f.write(private_key.encode())
        f.close()
        with open("pri.key", 'wb') as f:
            f.write(public_key.encode())
        f.close()
    return private_key, public_key

#ECC will encrypt data using plain text adn public key
def ECCEncrypt(plainText, public_key):
    cpabe_encrypt = encrypt(public_key, plainText)
    return cpabe_encrypt

#ECC will decrypt data using private key and encrypted text
def ECCDecrypt(encrypt, private_key):
    cpabe_decrypt = decrypt(private_key, encrypt)
    return cpabe_decrypt

def readDetails(contract_type):
    global details
    details = ""
    print(contract_type+"======================")
    blockchain_address = 'http://127.0.0.1:9545' #Blokchain connection IP
    web3 = Web3(HTTPProvider(blockchain_address))
    web3.eth.defaultAccount = web3.eth.accounts[0]
    compiled_contract_path = 'SmartContract.json' #Blockchain SmartContract calling code
    deployed_contract_address = '0xA3d8857d4E2F59eEa629a2042Bd97D80d240a90C' #hash address to access Shared Data contract
    with open(compiled_contract_path) as file:
        contract_json = json.load(file)  # load contract info as JSON
        contract_abi = contract_json['abi']  # fetch contract's abi - necessary to call its functions
    file.close()
    contract = web3.eth.contract(address=deployed_contract_address, abi=contract_abi) #now calling contract to access data
    if contract_type == 'signup':
        details = contract.functions.getSignup().call()
    if contract_type == 'userdata':
        details = contract.functions.getData().call()          
    print(details)    

def saveDataBlockChain(currentData, contract_type):
    global details
    global contract
    details = ""
    blockchain_address = 'http://127.0.0.1:9545'
    web3 = Web3(HTTPProvider(blockchain_address))
    web3.eth.defaultAccount = web3.eth.accounts[0]
    compiled_contract_path = 'SmartContract.json' #Blockchain contract file
    deployed_contract_address = '0xA3d8857d4E2F59eEa629a2042Bd97D80d240a90C' #contract address
    with open(compiled_contract_path) as file:
        contract_json = json.load(file)  # load contract info as JSON
        contract_abi = contract_json['abi']  # fetch contract's abi - necessary to call its functions
    file.close()
    contract = web3.eth.contract(address=deployed_contract_address, abi=contract_abi)
    readDetails(contract_type)
    if contract_type == 'signup':
        details+=currentData
        msg = contract.functions.setSignup(details).transact()
        tx_receipt = web3.eth.waitForTransactionReceipt(msg)
    if contract_type == 'userdata':
        details+=currentData
        msg = contract.functions.setData(details).transact()
        tx_receipt = web3.eth.waitForTransactionReceipt(msg)    

def index(request):
    if request.method == 'GET':
       return render(request, 'index.html', {})

def Login(request):
    if request.method == 'GET':
       return render(request, 'Login.html', {})

def Signup(request):
    if request.method == 'GET':
       return render(request, 'Signup.html', {})

def UploadFile(request):
    if request.method == 'GET':
       global username       
       return render(request, 'UploadFile.html', {})

def DownloadFileDataRequest(request):
    if request.method == 'GET':
        global dec_time
        hashcode = request.GET.get('hash', False)
        filename = request.GET.get('file', False)
        #content = api.get_pyobj(hashcode)
        with open("CloudApp/static/files/"+filename, "rb") as file:
            ecc_encrypt = file.read()
        file.close()
        private_key, public_key = ECCGenerateKeys()
        decrypted = ECCDecrypt(ecc_encrypt, private_key)
        response = HttpResponse(decrypted,content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename='+filename
        return response
        
            
def DownloadFile(request):
    if request.method == 'GET':
        global username
        strdata = '<table border=1 align=center width=100%><tr><th><font size="" color="black">Data Owner</th>'
        strdata+='<th><font size="" color="black">IPFS File Address</th><th><font size="" color="black">Upload Date Time</th>'
        strdata+='<th><font size="" color="black">Filename</th>'
        strdata+='<th><font size="" color="black">Download File</th></tr>'
        readDetails('userdata')
        arr = details.split("\n")
        for i in range(len(arr)-1):
            array = arr[i].split("#")
            if array[0] == username:
                strdata+='<tr><td><font size="" color="black">'+str(array[0])+'</td><td><font size="" color="black">'+array[1]+'</td><td><font size="" color="black">'+str(array[2])+'</td>'
                strdata+='<td><font size="" color="black">'+str(array[3])+'</td>'
                strdata+='<td><a href=\'DownloadFileDataRequest?hash='+array[1]+'&file='+array[3]+'\'><font size=3 color=black>Download File</font></a></td></tr>'                
        context= {'data':strdata}
        return render(request, 'ViewSharedMessages.html', context)        
         

def LoginAction(request):
    if request.method == 'POST':
        global username
        username = request.POST.get('t1', False)
        password = request.POST.get('t2', False)
        readDetails('signup')
        arr = details.split("\n")
        status = "none"
        for i in range(len(arr)-1):
            array = arr[i].split("#")
            if array[0] == username and password == array[1]:
                status = "Welcome "+username
                break
        if status != 'none':
            context= {'data':status}
            return render(request, 'UserScreen.html', context)
        else:
            context= {'data':'login failed'}
            return render(request, 'Login.html', context)

        
def UploadFileAction(request):
    if request.method == 'POST':
        global username
        filename = request.FILES['t1'].name
        myfile = request.FILES['t1'].read()
        #myfile = pickle.dumps(myfile)
        private_key, public_key = ECCGenerateKeys()
        ecc_encrypt = ECCEncrypt(myfile, public_key)
        now = datetime.datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        with open("CloudApp/static/files/"+filename, "wb") as file:
            file.write(ecc_encrypt)
        data = username+"#"+str(filename)+"#"+str(current_time)+"#"+filename+"\n"
        saveDataBlockChain(data,"userdata")
        output = 'Shared Data saved in Blockchain with below filename.<br/>'+str(filename)
        context= {'data':output}
        return render(request, 'UploadFile.html', context)
        
        
def SignupAction(request):
    if request.method == 'POST':
        global details
        username = request.POST.get('t1', False)
        password = request.POST.get('t2', False)
        contact = request.POST.get('t3', False)
        gender = request.POST.get('t4', False)
        email = request.POST.get('t5', False)
        address = request.POST.get('t6', False)
        output = "Username already exists"
        readDetails('signup')
        arr = details.split("\n")
        status = "none"
        for i in range(len(arr)-1):
            array = arr[i].split("#")
            if array[1] == username:
                status = username+" already exists"
                break
        if status == "none":
            details = ""
            data = username+"#"+password+"#"+contact+"#"+gender+"#"+email+"#"+address+"\n"
            saveDataBlockChain(data,"signup")
            context = {"data":"Signup process completed and record saved in Blockchain"}
            return render(request, 'Signup.html', context)
        else:
            context = {"data":status}
            return render(request, 'Signup.html', context)











        


