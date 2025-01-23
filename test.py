from ResourceManager import ResourceManager
from UserContextInterface import UserContextInterface

rm = ResourceManager(location_interface_map = {
             "chat_history": ChatHistoryInterface()
         })

rm.set("chat_history/1",{
    "some data":"some object"
})

rm.set("chat_history/2",{
    "some other data":"some other object"
})

print(rm.get("chat_history/1"))
print(rm.get("chat_history/4"))