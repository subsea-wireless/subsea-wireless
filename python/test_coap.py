import aiocoap
from cobs import cobs

def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    poly = 0x1021
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def append_crc16(data: bytes) -> bytes:
    crc = crc16_ccitt(data)
    return data + crc.to_bytes(2, "big")


def crc_test(data: bytes):
    crc = crc16_ccitt(data)
    print(f"CRC16-CCITT for {data} is {crc:#06x}")
    data_with_crc = append_crc16(data)
    print(f"Data with CRC: {data_with_crc}")
    # Verify the CRC
    received_data = data_with_crc[:-2]
    received_crc = int.from_bytes(data_with_crc[-2:], "big")
    calculated_crc = crc16_ccitt(received_data)
    if received_crc == calculated_crc:
        print("CRC verification successful.")
    else:
        print("CRC verification failed.")


def request(code, payload, mid):
    """ Send a GET request, payload is a SWiG COBS Protobuf message"""
    request = aiocoap.Message(code=code, payload=payload)
    request.mid = mid    # May want to manage with a Context
    request.mtype = aiocoap.CON
    print(f'Sending {request}')
    return request


def receive(message_bytes):
    """ Receive a message from the wire, decode and parse it"""
    message = aiocoap.Message.decode(message_bytes)
    print(f'Received {message}')
    payload = message.payload
    return message


def respond(message, payload=b''):
    """ Assemble a response to the provided Message"""
    response = aiocoap.Message()
    if len(payload):
        response.code = aiocoap.CONTENT
    else:
        response.code = aiocoap.EMPTY
    response.mtype = aiocoap.ACK
    response.mid = message.mid
    response.payload = payload
    print(f'Responding with {message}')
    return response


def run_GET_test():
    print("GET example message flow")
# Create a request
    message = request(code=aiocoap.GET, payload=b'SWiG Protobuf request packet placeholder', mid=0x5347)
    message_bytes = message.encode()    # Ready to send on the wire
    print(f"UDP CoAP message: [{message_bytes}]")

    # Demonstrate what would be sent over serial
    serial_crc = crc16_ccitt(message_bytes).to_bytes(2, "big")
    serial_message = bytes([0x00]) + cobs.encode(message_bytes + serial_crc) + bytes([0x00])
    print(f"Serial message (Protobuf + CoAP + CRC + COBS + delimiters): [{serial_message}]")
    
    message = receive(message_bytes)

    if message.code.is_request():
        print(f'Request- payload is {message.payload}')
    else:
        print(f'Not a request, code is {message.code}')
    
# Respond to the request
    message = respond(message, b'SWiG Protobuf response packet placeholder')
    response_bytes = message.encode()   # Ready to send on the wire
    print(f"Serial response: [{response_bytes}]")
    
    message = receive(response_bytes)

    if message.code.is_response():
        print(f'Response- payload is {message.payload}')
    else:
        print(f'Not a response, code is {message.code}')


def run_POST_test():
    print("\nPOST example message flow")
# Create a request
    message = request(code=aiocoap.POST, payload=b'SWiG Protobuf value setting placeholder', mid=0x5350)
    message_bytes = message.encode()    # CoAP ready to send on UDP or wrap for serial
    print(f"UDP message: [{message_bytes}]")
    serial_crc = bytes([0x43, 0x52])

    # Demonstrate what would be sent over serial
    serial_crc = crc16_ccitt(message_bytes).to_bytes(2, "big")
    serial_message = bytes([0x00]) + cobs.encode(message_bytes + serial_crc) + bytes([0x00])
    print(f"Serial message (Protobuf + CoAP + CRC + COBS + delimiters): [{serial_message}]")
    
    message = receive(message_bytes)

    if message.code.is_request():
        print(f'Request- payload is {message.payload}')
    else:
        print(f'Not a request, code is {message.code}')
    
# Respond to the request
    message = respond(message)  # ACK with no payload
    response_bytes = message.encode()   # Ready to send on the wire
    print(f"Serial response: [{response_bytes}]")
    
    message = receive(response_bytes)

    if message.code.is_response():
        print(f'Response- payload is {message.payload}')
    else:
        print(f'Not a response, code is {message.code}')


def main():
    # print ("CRC16-CCITT test")
    # crc_test(str.encode("CRC Test Packet"))

    print("SWiG CoAP message flow with aiocoap")
    run_GET_test()  # Used to get a parameter or status value
    run_POST_test() # Set a parameter value


if __name__ == "__main__":
    main()
    