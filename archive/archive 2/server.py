import asyncio
import websockets
import json
import random
import mysql.connector

PORT = 8080
SERVER = "localhost"

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
        chatroomID, chatroomName, username = user_chatroom_tuple
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
                mycursor.execute("INSERT INTO `user_chatroom` (`chatroomID`, `chatroomName`, `username`) VALUES (%s, %s, %s)", data)

                # send the chatroom to the creator
                newChatroomMessage = {"chatcode": random_numbers, "chatname": chatroomName , "type": "newChatroom"}
                await websocket.send(json.dumps(newChatroomMessage))

                await broadcast(json.dumps(user_chatroomEntry))

            elif message_type == "joinChatroom":
                chatroomCode =  message_data.get("chatcode", "")

                chatcode_exists = False

                isAlreadyJoined = False

                chatroomName = ""

                chatrooms = [json.loads(chatroom) for chatroom in chatroomList]
                print(chatrooms)

                print(chatroomCode)
                for chatroom in chatrooms:  
                    if (chatroomCode == str(chatroom['chatcode'])):
                        chatroomName = chatroom['chatname']
                        chatcode_exists = True
                
                # user_chatroom_record = [json.loads(user_chatrooms) for user_chatrooms in user_chatroom]

                if chatcode_exists:
                    # for uChatroom in user_chatroom_record:
                    #     if(uChatroom['chatcode'] == chatroomName and uChatroom['username'] == socketUsername):
                    #         isAlreadyJoined = True
                        
                    if(isAlreadyJoined):
                        newChatroomMessage = {"type": "alert", "message": "You are already joined"}
                        await websocket.send(json.dumps(newChatroomMessage))

                    else:
                        print("Chatcode exists in the list.")
                        user_chatroomEntry = {"chatcode": chatroomCode,  "chatname": chatroomName,  "username": socketUsername, "type": "user-chatroom"}
                        user_chatroom.append(json.dumps(user_chatroomEntry))
                        print(user_chatroom)     

                        # save to database
                        data = (chatroomCode, chatroomName, socketUsername)
                        mycursor.execute("INSERT INTO `user_chatroom` (`chatroomID`, `chatroomName`, `username`) VALUES (%s, %s, %s)", data)
                        
                        await broadcast(json.dumps(user_chatroomEntry))

                else:
                    newChatroomMessage = {"type": "alert", "message": "Chatroom does not exist"}
                    await websocket.send(json.dumps(newChatroomMessage))
                    print("Chatcode does not exist in the list.")
 
            elif message_type == "logout":
                print("logging out")
                await websocket.close()

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
