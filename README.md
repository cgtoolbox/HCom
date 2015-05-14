# HCom
HCom is a client / server communication system which allows the user to send data between software like Houdini and Maya through local network. It allows to send meshes, bitmaps, and houdini digital assets ( more to come soon ... ).

It is based on Python 2.7 and the rpyc library, the UI is written with PySide ( shipped with Houdini and Maya ).

How it works:

- A hCom python server runs on a machine on the network
- On each user machine you can connect an hCom client ( from Maya or/and Houdini )  to the server.
- you can send data to any user connected to hCom, for houdini digital assets, only maya with Houdini Engine installed can receive them.

Demo on vimeo:

Help : http://guillaumejobst.blogspot.fr/p/hcom.html

https://vimeo.com/127091487 ( Houdini to Houdini )

https://vimeo.com/127655675 ( Houdini to Maya )


