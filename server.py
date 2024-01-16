import asyncio
import websockets
import json
import random
import mysql.connector

PORT = 8080
SERVER = 'localhost'

conn = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database ="chat",
  autocommit=True
)

if(conn.is_connected()):
    print("Connected to Databse")
else:
    print("connection to Database failed")

mycursor = conn.cursor()

def RetrieveData():
    mycursor.execute("SELECT * FROM users")
    usersquery = mycursor.fetchall()

    for userTuple in usersquery:
        userID, username, password = userTuple
        users.append(json.dumps({"username": username,  "password": password, "type": "user"}))
    print("[server]: Users retrieved")

    mycursor.execute("SELECT * FROM `messages`")
    messagequery = mycursor.fetchall()

    for messagesTuple in messagequery:
        chatID, chatroomID, username, message = messagesTuple
        message_history.append(json.dumps({"chatroom": chatroomID, "username": username, "message": message, "type": "message"}))
    print("[server]: past messages retrieved")


    mycursor.execute("SELECT * FROM `chatrooms`")

    chatroomsquery = mycursor.fetchall()

    for chatroomsTuple in chatroomsquery:
        chatroomID, chatroomName = chatroomsTuple
        chatroomList.append(json.dumps({"chatcode": chatroomID, "chatname": chatroomName, "type": "chatroom"}))
    print("[server]: chatrooms retrieved")

    mycursor.execute("SELECT * FROM `user_chatroom`")

    user_chatroom_query = mycursor.fetchall()

    for user_chatroom_tuple in user_chatroom_query:
        chatroomID, chatroomName, username, isApproved, isAdmin = user_chatroom_tuple
        user_chatroom.append(json.dumps({"chatcode": chatroomID,  "chatname": chatroomName,  "username": username, "type": "user-chatroom"}))
    print("[server]: user_chatroom retrieved")

# format: '{"chatroom": currentChatroom, "username": username, "message": message, "type": "message"}'
message_history = []

# format: '{"chatcode": chatroomCode,  "chatname": chatroomName,  "username": socketUsername, "type": "user-chatroom"}'
user_chatroom = [
    # '{"chatcode": "222222",  "chatname": "chatroomName",  "username": "Raven", "type": "user-chatroom"}',
    # '{"chatcode": "222222",  "chatname": "chatroomName",  "username": "jordan", "type": "user-chatroom"}'
]

# format: '{"chatcode": random_numbers, "chatname": chatroomName, "type": "chatroom"}'
chatroomList = [
    # '{"chatcode": "222222", "chatname": "chatroomName", "type": "chatroom"}'
]   

# sample users... for dubugging purpose
# format: '{"username": "Raven",  "password": "12345", "type": "user"}'
users = [
    # '{"username": "Raven",  "password": "1", "type": "user"}',
    # '{"username": "jordan",  "password": "2", "type": "user"}'
]

#format: {"username": "name here", "type": "status"}
active_users = [
    # '{"username": "jordan", "type": "status"}'
]

async def handle(websocket, path):
    clients.add(websocket)

    socketUsername = ""
    try:
        async for message in websocket:
            message_data = json.loads(message)
            message_type = message_data.get("type", "")

            if message_type == "message":
                currentChatroom = message_data.get("chatroom", "")
                currentMessage = message_data.get("message", "")

                # save message to database
                data = (currentChatroom, socketUsername, currentMessage)
                mycursor.execute("INSERT INTO `messages` (`chatroomID`, `username`, `message`) VALUES (%s, %s, %s)", data)
                
                message_history.append(message)
                await broadcast(message)
            
            elif (message_type == "loginUser"):
                loginUsernames = message_data.get("username", "")
                loginPassword = message_data.get("password", "")

                storedUser = [json.loads(storedUsers) for storedUsers in users]

                usernameExist = False
                passwordMatch = False

                # check if user exist
                for user in storedUser:
                    if(loginUsernames == user['username']):
                        # check password 
                        if(loginPassword == user['password']):
                            serverMessage = {"username": loginUsernames, "type": "login"}  

                            socketUsername = loginUsernames
                            
                            await websocket.send(json.dumps(serverMessage))

                            # send all past messages
                            await send_all_messages(websocket)

                            # send all user-chatroom connection
                            await send_all_chatroom(websocket)

                            # send all current active users
                            await send_all_active(websocket)

                            # send message to other user that you're online
                            yourActiveEntry = {"username": socketUsername, "type": "status"}
                            await broadcast(json.dumps(yourActiveEntry))

                            activeUsersEntry = {"username": loginUsernames, "type": "status"}
                            active_users.append(json.dumps(activeUsersEntry))
                            print(f"current active users: {active_users}")

                            print(f"[{socketUsername}]: Logging in...")

                            usernameExist = True
                            passwordMatch = True
                            break
                        
                        usernameExist = True
                        break
                
                if(not usernameExist):
                    serverMessage = {"type": "alert", "message": "user does not exist"}
                    await websocket.send(json.dumps(serverMessage))
                elif(not passwordMatch):
                    serverMessage = {"type": "alert", "message": "Wrong password"}
                    await websocket.send(json.dumps(serverMessage))

            elif (message_type == "signupUser"):
                signupUsernames = message_data.get("username", "")
                signupPassword = message_data.get("password", "")

                usernameExist = False

                # load the json -- convert json to dictionary
                storedUser = [json.loads(storedUsers) for storedUsers in users]
                # check if user exist
                for user in storedUser:
                    if(signupUsernames == user['username']):
                        serverMessage = {"type": "alert", "message": "Username is already taken."}
                        await websocket.send(json.dumps(serverMessage))
                        usernameExist = True
                        break
                
                # create username
                if(not usernameExist):
                    # save it on database
                    data = (signupUsernames, signupPassword)
                    mycursor.execute("INSERT INTO users (`username`, `password`) VALUES (%s, %s)", data)

                    # save it on runtime
                    userEntry = {"username": signupUsernames,  "password": signupPassword, "type": "user"}
                    users.append(json.dumps(userEntry))

                    # send a response to socket
                    serverMessage = {"type": "alert", "message": "Account created."}
                    await websocket.send(json.dumps(serverMessage))

                    print(f"[server]: creating user: {signupUsernames}")

            elif message_type == "getChatroomUsers": 
                print("getting chatroom users")
                chatroom = message_data.get("chatcode", "")
                chatroom_users = []
                user_chatroom_record = [json.loads(user_chatrooms) for user_chatrooms in user_chatroom]
                for uChatroom in user_chatroom_record:

                    if(uChatroom['chatcode'] == chatroom):
                        chatroom_users.append(json.dumps(uChatroom))
                user_chatroomEntry = {"chatcode": chatroom, "type": "user-chatroom"}
                print(chatroom_users)
                print(user_chatroom_record)
                await websocket.send(json.dumps(user_chatroomEntry))
                
            elif message_type == "createChatroom":
                # create a chatroom and save it to chatroom list
                chatroomName = message_data.get("chatroomName", "")
                random_numbers = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                newChatroomEntry = {"chatcode": random_numbers, "chatname": chatroomName, "type": "chatroom"}
                chatroomList.append(json.dumps(newChatroomEntry))

                data = (random_numbers, chatroomName)
                mycursor.execute("INSERT INTO `chatrooms` (`chatroomID`, `chatroomName`) VALUES (%s, %s)", data)
                # save the new chatroom to database

                #add the new chatroom to the creator's chatroom_user list
                user_chatroomEntry = {"chatcode": random_numbers,  "chatname": chatroomName,  "username": socketUsername, "type": "user-chatroom"}
                user_chatroom.append(json.dumps(user_chatroomEntry))

                # save the user_chatroom to database
                data = (random_numbers, chatroomName, socketUsername)
                mycursor.execute("INSERT INTO `user_chatroom` (`chatroomID`, `chatroomName`, `username`, `is_approved`, `role`) VALUES (%s, %s, %s, 1, 'admin')", data)

                # send the chatroom to the creator
                newChatroomMessage = {"chatcode": random_numbers, "chatname": chatroomName , "type": "newChatroom"}
                await websocket.send(json.dumps(newChatroomMessage))

                await broadcast(json.dumps(user_chatroomEntry))

            elif message_type == "joinChatroom":
                chatroomCode =  message_data.get("chatcode", "")

                chatcode_exists = False
                isAdmin = False
                isAlreadyJoined = False
                isApproved = False
                chatroomName = ""

                chatrooms = [json.loads(chatroom) for chatroom in chatroomList]
                print(chatroomCode)
                for chatroom in chatrooms:  
                    if (chatroomCode == str(chatroom['chatcode'])):
                        chatroomName = chatroom['chatname']
                        chatcode_exists = True
                
                user_chatroom_record = [json.loads(user_chatrooms) for user_chatrooms in user_chatroom]

                if chatcode_exists:
                    for uChatroom in user_chatroom_record:
                        
                        if(uChatroom['chatname'] == chatroomName and uChatroom['username'] == socketUsername):
                            isAlreadyJoined = True
                        
                    if(isAlreadyJoined):
                        newChatroomMessage = {"type": "alert", "message": "You are already joined"}
                        await websocket.send(json.dumps(newChatroomMessage))

                    else:
                        print("Chatcode exists in the list.")
                        
                        # check if the user is approved 
                        
                        query = f"SELECT * FROM `user_chatroom` WHERE `chatroomID` = 'd{chatroomCode}' AND `username` = '{socketUsername}'"
                    
                        mycursor.execute(query) 
                        result = mycursor.fetchall()
                        
                        # check if the user is approved 
                        
                        for row in result:
                            if(row[3] == 1):
                                isApproved = True
                                break
                            if (row[4] == "admin"):
                                isAdmin = True
                                isApproved = True
                                break
                        user_chatroomEntry = {"chatcode": chatroomCode,  "chatname": chatroomName,  "username": socketUsername, "type": "user-chatroom"}
                        print(chatroomName, socketUsername)
                        user_chatroom.append(json.dumps(user_chatroomEntry))
                        print(user_chatroom)     

                        # save to database
                        data = (chatroomCode, chatroomName, socketUsername)

                        mycursor.execute("INSERT INTO `user_chatroom` (`chatroomID`, `chatroomName`, `username`) VALUES (%s, %s, %s)", data)
                        
                        
                        if (not isApproved):
                            print("...not approved")
                            newChatroomMessage = {"type": "alert", "message": "Waiting for approval to join this chatroom"}
                            await websocket.send(json.dumps(newChatroomMessage))
                            break
                        
                        
                        await broadcast(json.dumps(user_chatroomEntry))

                else:
                    newChatroomMessage = {"type": "alert", "message": "Chatroom does not exist"}
                    await websocket.send(json.dumps(newChatroomMessage))
                    print("Chatcode does not exist in the list.")
 
            elif message_type == "logout":
                print("logging out")
                await websocket.close()
                
            elif message_type == "approve":
                print("approving user")
                username = message_data.get("username", "")
                chatcode = message_data.get("chatcode", "")

                # update the database
                query = f"UPDATE `user_chatroom` SET `is_approved`= 1 WHERE `chatroomID` = '{chatcode}' AND `username` = '{username}'"
                mycursor.execute(query)
                
                query = f"SELECT * FROM `user_chatroom` WHERE `chatroomID` = '{chatcode}' AND `is_approved` = 0"
                mycursor.execute(query)
                result = mycursor.fetchall()
                if result:
                    for row in result:
                        username = row[2]
                        if username:
                            user_chatroom_entry = {"chatcode": chatcode,  "username": username, "type": "toApprove", "isAdmin": isAdmin, "message": "There are users to approve"}
                            await websocket.send(json.dumps(user_chatroom_entry))
                
                else:
                    user_chatroom_entry = {"chatcode": chatcode,  "username": username, "type": "toApprove", "isAdmin": isAdmin, "message": "No users to approve"}
                    await websocket.send(json.dumps(user_chatroom_entry))
             

            elif message_type == "isAllowed":
                # check if the user is allowed to join the chatroom 
                
                chatcode = message_data.get("chatcode", "")
                username = message_data.get("username", "")

                
                query = f"SELECT * FROM `user_chatroom` WHERE `chatroomID` = '{chatcode}' AND `username` = '{username}' AND `is_approved` = 1"
                
                mycursor.execute(query) 
                result = mycursor.fetchall()
                RetrieveData()
                if result: 
                    message = {"chatcode": chatcode,  "username": username, "type": "isAllowed", "message": "Allowed"}
                    await websocket.send(json.dumps(message))
                else:
                    message = {"chatcode": chatcode,  "username": username, "type": "isAllowed", "message": "Not Allowed"}
                    await websocket.send(json.dumps(message))
                    
                
                
            
            elif message_type == "getToApprove": 
              
                print("getting to approve")
                chatcode = message_data.get("chatcode", "")
                username = message_data.get("username", "")
                print(chatcode, username)
                # get all the users that are not approved
                isAdmin = False
                
                checkAdmin = f"SELECT * FROM `user_chatroom` WHERE `chatroomID` = '{chatcode}' AND `username` = '{username}' AND `role` = 'admin'"
                print(checkAdmin)
                mycursor.execute(checkAdmin)
                result = mycursor.fetchall()
                
                print(result)
                if (result):
                    print("admin")
                    isAdmin = True
                    
                if (not isAdmin):
                    print("not admin")
                    user_chatroom_entry = {"chatcode": chatcode, "username": username, "type": "toApprove", "isAdmin": isAdmin, "message": "You are not an admin"}
                    await websocket.send(json.dumps(user_chatroom_entry))

        
                
                else:
                    query = f"SELECT * FROM `user_chatroom` WHERE `chatroomID` = '{chatcode}' AND `is_approved` = 0"
                    mycursor.execute(query)
                    result = mycursor.fetchall()

                    if result:
                        for row in result:
                            username = row[2]
                            print(username)
                            if username:
                                user_chatroom_entry = {"chatcode": chatcode,  "username": username, "type": "toApprove", "isAdmin": isAdmin, "message": "There are users to approve"}
                                await websocket.send(json.dumps(user_chatroom_entry))
                    else:
                        user_chatroom_entry = {"chatcode": chatcode,  "username": username, "type": "toApprove", "isAdmin": isAdmin, "message": "No users to approve"}
                        await websocket.send(json.dumps(user_chatroom_entry))
                     

    finally:
        clients.remove(websocket)
        # remove active status to client side
        removeActiveEntry = {"username": socketUsername, "type": "removeActive"}
        await broadcast(json.dumps(removeActiveEntry))


        # remove active status in server side
        await remove_active_status(socketUsername)
        print(f"User {websocket} has left the chat.")

async def remove_active_status(username):
    # convert the json to dictionary
    global active_users
    user_objects = [json.loads(user) for user in active_users]

    # get the index of the username     
    index_to_remove = None
    for index, user in enumerate(user_objects):
        if user['username'] == username:
            index_to_remove = index
            break 

    # delete it from the dictionary
    if index_to_remove is not None:
        del user_objects[index_to_remove]
    
    # convert the modified dictionary to json string and save it to active users
    active_users = [json.dumps(user) for user in user_objects]

    print(f"current users after logging out: {active_users}")

async def send_all_messages(client):
    for past_message in message_history:
        await client.send(past_message)

async def send_all_chatroom(client):
    for chatrooms in user_chatroom:
        await client.send(chatrooms)

async def send_all_active(client):
    for active in active_users:
        await client.send(active)

async def broadcast(message):
    for client in clients:
        await client.send(message)


clients = set()

start_server = websockets.serve(handle, SERVER, PORT)

print("SERVER: Starting...")
print(f"SERVER: Listening on {SERVER}:{PORT}")

RetrieveData()

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
