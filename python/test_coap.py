from common import *

###### Test functions to demonstrate/test the shared functions and perform typical message flows

def crc_test(data: bytes, expected):
    crc = crc16_ccitt(data)
    print(f"CRC16-CCITT for {data} is {crc:#06x}")
    crc = crc16_ccitt(data)
    if crc == expected:
        print(f"Calculated CRC 0x{crc:02X} equals provided expected CRC")
    else:
        raise ValueError(f"CRC fail, calculated 0x{crc:02X} expected 0x{expected:02X}")


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
    # crc_test(str.encode("CRC Test Packet"), 0x5931) # Pass pre-validated expected result from https://www.codertools.net/tools/crc.php (CRC-16/CCITT-FALSE)

    print("SWiG CoAP message flow with aiocoap")
    run_GET_over_serial_test()  # Used to get a parameter or status value
    run_POST_over_UDP_test() # Set a parameter value


if __name__ == "__main__":
    main()
    