import constants
import commands

"""
Description:

Helper class that encapsulates utilities for the server that do not depend on a server state.

"""
class ServerUtil:

    @staticmethod
    def get_command_type(request):
        request_split = request.split(' ')
        command_type = request_split[1] if constants.COMMAND_PREFIX_DELIM in request_split[0] else request_split[0]
        return command_type

    # Extract message from the PRIVMSG request
    @staticmethod
    def get_broadcast_message(request):
        message = request[request.find(constants.COMMAND_MESSAGE_DELIM, 1) + 1:request.index(constants.COMMAND_END_DELIM)]
        return message

    # Extract message from the NICK request
    @staticmethod
    def get_nickname_message(request):
        nickname = request[request.index(commands.NICKNAME) + len(commands.NICKNAME):request.index(constants.COMMAND_END_DELIM)]
        return nickname.strip()

    # Extract message from the User request
    @staticmethod
    def get_username_message(request):
        pass

    @staticmethod
    def get_request_from_buffer(buffered_request):
        request_delim = buffered_request.index(constants.COMMAND_END_DELIM) + len(constants.COMMAND_END_DELIM)
        request = buffered_request[:request_delim]
        return request, request_delim

    @staticmethod
    def build_response(message):
        response = f'{message}{constants.COMMAND_END_DELIM}'
        response = response.encode(constants.COMMAND_ENCODING)
        return response

