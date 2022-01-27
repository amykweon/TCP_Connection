import socket
import struct
import array
import sys

packet_buffer = dict()

sourceip = 0
sourceport = 0
recvport = 0
window = 0

def checksum(msg):
	if len(msg) % 2 != 0:
		msg += b'\0'
	res = sum(array.array("H", msg))
	res = (res >> 16) + (res & 0xffff)
	res += res >> 16
	res = (~res) & 0xffff
	return res

def ack_packet(header):
	tcp_source = header[0]
	tcp_dest = header[1]
	tcp_seq = header[2]
	tcp_ack_seq = header[3]

	#tcp flags
	tcp_fin = header[5] & 0x1
	tcp_syn = (header[5] & 0x2) >> 2
	tcp_ack = 1
	tcp_check = header[7]
	tcp_window = header[6]

	#tcp flags not used
	tcp_rst = 0
	tcp_psh = 0
	tcp_urg = 0
	tcp_urg_ptr = 0

	tcp_offset_res = header[4]
	tcp_flags = tcp_fin + (tcp_syn << 1) + (tcp_rst << 2) + (tcp_psh << 3) + (tcp_ack << 4) + (tcp_urg << 5)

	ack_packet = struct.pack('!HHLLBBH', tcp_source, tcp_dest, tcp_seq, tcp_ack_seq, tcp_offset_res, tcp_flags, tcp_window) + struct.pack('H', tcp_check) + struct.pack('!H', tcp_urg_ptr)
	
	return ack_packet

if __name__ == '__main__':
	if (len(sys.argv) != 5):
		print("python3 tcpclient.py <file> <listening port> <address for ack> <ack port number>")
		sys.exit()

	file = sys.argv[1]
	# define global variables
	fileport = int(sys.argv[2])
	ackip = sys.argv[3]
	ackport = int(sys.argv[4])
	
	f = open(file, "wb")
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind(('0.0.0.0', fileport))

	seq_base = 0 # indicates the ordering of writting
	writing = True
	while writing:
		packet = sock.recv(596)
		header = struct.unpack('!HHLLBBHHH', packet[0:20])
		msg = packet[20:]
		
		# check corrupted bit
		if (checksum(packet) != 0):
			continue

		# create and send ACK
		ack = ack_packet(header)
		sock.sendto(ack, (ackip, ackport))

		# save arrived packet and sort it with index converted from sequence number
		seq_index = header[2] // 576
		packet_buffer[seq_index] = packet
		sequence_number = list(packet_buffer.keys())
		sequence_number.sort()

		for seq in sequence_number:
			if (seq == seq_base):
				# message portion written to file
				f.write(packet_buffer[seq][20:])

				# TCP header detect final file written
				header = struct.unpack('!HHLLBBHHH', packet_buffer[seq][:20])
				if (header[5] & 0x1):
					writing = False
				
				# written packet flagged to remove
				packet_buffer[seq] = -1
				seq_base +=1
		
		# remove entry of written packets
		packet_buffer = {i:packet_buffer[i] for i in packet_buffer if packet_buffer[i]!= -1}

	print("Written all data to {}".format(file))
	f.close()
	sock.close()