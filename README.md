# HCom
Hcom is a client – server communication system wrapped in a Pypanel in Houdini 14 ( 14.0.291 recommended ).
It allows users to send data from a Houdini session to another session throught local network.

You can send nodes or digital assets, even if the Houdini target client doesn't have access to that asset, Hcom will install it for you in your current session.
You can send also meshes as bgeo or obj format ( alembic coming soon … ) as well as image files.

To launch the server, you only need python 2.7.x and the rpyc library ( also shipped with Houdini ).
For the interface and the client side, everything you need ( PySide and rpyc ) is included in Houdini 14.x
