import constants
import commands

"""
Description:

Helper class that encapsulates utilities for the server that do not depend on a server state.

"""
class ServerUtil:

    # Get command type from any message
    @staticmethod
    def get_command_type(request):
        request_split = request.split()
        command_type = request_split[1] if constants.COMMAND_PREFIX_DELIM in request_split[0] else request_split[0]
        return command_type

    # Extract message from the PRIVMSG request
    @staticmethod
    def get_broadcast_message(request):
        message = request[request.find(constants.COMMAND_MESSAGE_DELIM, 1) + 1:request.index(constants.COMMAND_END_DELIM)]
        return message.strip()

    # Extract message from the NICK request
    @staticmethod
    def get_nick_nickname(request):
        nickname_index = request.index(commands.NICKNAME) + len(commands.NICKNAME)
        nickname = request[nickname_index:request.find(' ', nickname_index + 1)]
        return nickname.strip()

    # Extract message from the USER request
    @staticmethod
    def get_user_username(request):
        username_index = request.index(commands.USERNAME) + len(commands.USERNAME) # username start
        username = request[username_index:request.find(' ', username_index + 1)]
        return username.strip()

    # Verify username message has enough params
    @staticmethod
    def user_valid_params(request):
        request_split = request.split()
        return len(request_split) >= 5

    # Get next request from the buffer
    @staticmethod
    def get_request_from_buffer(buffered_request):
        request_delim = buffered_request.index(constants.COMMAND_END_DELIM) + len(constants.COMMAND_END_DELIM)
        request = buffered_request[:request_delim]
        return request, request_delim

