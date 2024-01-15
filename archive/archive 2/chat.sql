CREATE DATABASE IF NOT EXISTS chat;

USE chat;

CREATE TABLE users (
  `userID` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(256) NOT NULL,
  `password` varchar(256) NOT NULL,
  PRIMARY KEY (userID)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE chatrooms (
    `chatroomID` int(11) NOT NULL,
    `chatroomName` varchar(256) NOT NULL,
    PRIMARY KEY (chatroomID) 
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE messages (
    `chatID` int(11) NOT NULL AUTO_INCREMENT,
    `chatroomID` int(11) NOT NULL,
    `username` varchar(256) NOT NULL,
    `message` varchar(256) NOT NULL,
    FOREIGN KEY (chatroomID) REFERENCES chatrooms(chatroomID),
    PRIMARY KEY (chatID)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE user_chatroom (
    `chatroomID` int(11) NOT NULL,
    `chatroomName` varchar(256) NOT NULL,
    `username` varchar(256) NOT NULL,
    FOREIGN KEY (chatroomID) REFERENCES chatrooms(chatroomID),
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


