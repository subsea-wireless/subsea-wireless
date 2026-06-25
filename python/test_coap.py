import aiocoap
from cobs import cobs


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    """ Calculate the CRC16-CCITT checksum for the given data with CRC specifications:
        polynomial 0x1021, initial value 0xFFFF, no final XOR, and no reflection.
        Verified against https://www.codertools.net/tools/crc.php     
    """
    poly = 0x1021
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def get_udp_message_bytes(code, protobuf, mid, mtype):
    """ Create a UDP message with the given code, protobuf, and message ID
        as a CoAP message byte stream, with the provided parameters
    """
    message = aiocoap.Message(code=code, payload=protobuf)
    message.mid = mid
    message.mtype = mtype
    return message.encode()


def get_serial_message_bytes(code, protobuf, mid, mtype):
    """ Create a serial message with the given code, protobuf, and message ID
        by wrapping the base CoAP message with checksum, COBS encoding, and null delimiters
    """
    message_bytes = get_udp_message_bytes(code, protobuf, mid, mtype)
    serial_crc = crc16_ccitt(message_bytes).to_bytes(2, "big")
    serial_message = bytes([0x00]) + cobs.encode(message_bytes + serial_crc) + bytes([0x00])
    return serial_message


def coap_message_from_udp_bytes(message_bytes):
    """ Extract the CoAP message from a UDP message"""
    message = aiocoap.Message.decode(message_bytes)
    return message


def coap_message_from_serial_bytes(serial_message):
    """ Extract the CoAP message from a serial message
        removing serial-specific framing and using 
        coap_message_from_udp_bytes to decode the CoAP message
    """
    # Remove any leading and trailing null COBS delimiter(s)
    while serial_message.startswith(b'\x00') and len(serial_message) > 1:
        serial_message = serial_message[1:]
    while serial_message.endswith(b'\x00') and len(serial_message) > 1:
        serial_message = serial_message[:-1]

    if len(serial_message) > 3: # data + CRC
        cobs_decoded = cobs.decode(serial_message)
        message_bytes = cobs_decoded[:-2]  # Remove CRC
        crc_received = int.from_bytes(cobs_decoded[-2:], "big")
        crc_calculated = crc16_ccitt(message_bytes)
        if crc_received == crc_calculated:
            return coap_message_from_udp_bytes(message_bytes)
        else:
            raise ValueError("Serial CRC mismatch")
    else:
        raise ValueError("Serial message too short")
    

###### Test functions to demonstrate/test the above functions and perform typical message flows


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


def run_GET_over_serial_test():
    print("GET example message flow")
# Create a request
    message_id = 0x5347
    payload = b'SWiG Protobuf request packet placeholder'

    # Prepare and 'send' serial bytes
    serial_message = get_serial_message_bytes(aiocoap.GET, protobuf = payload, mid = message_id, mtype = aiocoap.CON)
    print(f"Serial message (Protobuf + CoAP + CRC + COBS + delimiters): [{serial_message}]")
    
    # 'receive' and process serial bytes
    message = coap_message_from_serial_bytes(serial_message)

    if message.code.is_request():
        print(f'Request- payload is {message.payload}')
    else:
        print(f'Not a request, code is {message.code}')
    
    
    # Prepare and 'send' serial response
    payload = b'SWiG Protobuf response packet placeholder'
    if len(payload):
        code = aiocoap.CONTENT
    else:
        code = aiocoap.EMPTY
    response_bytes = get_serial_message_bytes(code = code, protobuf = payload, mid = message.mid, mtype = aiocoap.ACK)
    print(f"Serial response: [{response_bytes}]")
    
    # 'receive' and process the response
    message = coap_message_from_serial_bytes(response_bytes)

    if message.code.is_response():
        print(f'Response- payload is {message.payload}')
    else:
        print(f'Not a response, code is {message.code}')


def run_POST_over_UDP_test():
    print("\nPOST example message flow")
# Create a request
    message_id = 0x5350
    payload = b'SWiG Protobuf value setting placeholder'

    # Prepare and 'send' UDP bytes
    message_bytes = get_udp_message_bytes(aiocoap.POST, protobuf = payload, mid = message_id, mtype = aiocoap.CON)
    print(f"UDP message: [{message_bytes}]")

    # 'receive' and process UDP bytes
    message = coap_message_from_udp_bytes(message_bytes)

    if message.code.is_request():
        print(f'Request- payload is {message.payload}')
    else:
        print(f'Not a request, code is {message.code}')
    
    # Prepare and 'send' UDP response
    payload = b'SWiG Protobuf response packet placeholder'
    if len(payload):
        code = aiocoap.CONTENT
    else:
        code = aiocoap.EMPTY
    response_bytes = get_udp_message_bytes(code = code, protobuf = payload, mid = message.mid, mtype = aiocoap.ACK)
    print(f"UDP response: [{response_bytes}]")

    # 'receive' and process the response
    message = coap_message_from_udp_bytes(response_bytes)

    if message.code.is_response():
        print(f'Response- payload is {message.payload}')
    else:
        print(f'Not a response, code is {message.code}')


def main():
    # print ("CRC16-CCITT test")
    # crc_test(str.encode("CRC Test Packet"))

    print("SWiG CoAP message flow with aiocoap")
    run_GET_over_serial_test()  # Used to get a parameter or status value
    run_POST_over_UDP_test() # Set a parameter value


if __name__ == "__main__":
    main()
    