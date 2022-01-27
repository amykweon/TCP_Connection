==========================================================================================
File Descriptions:

	1. tcpserver.py
		The server (receiver) receives data from the specified listening port and sends
			ACK packet to specified ip address and port number.
		It writes the data into a file name specified.
		It implements Selective-Repeat version of TCP protocol. The buffer saves out of
			order packet and writes buffered packets and the packet in sequence arrives.

	2. tcpclient.py
		The client (sender) create TCP packets from a specified file. It sends the packets
			to specified ip address and port number. It recovers from packet loss,
			corrupted data, and packet delay with custom implemented TCP protocol.
		It implements Selective-Repeat version of TCP protocol. It stops retransmission
			when ACK is received regardless of the sequence. However, to move window
			in sequence, ACK is buffered.

	3. test_file.txt
		This is a test file to be used for tcpclient.py program to send to the server.
		Its size is 50KB.

==========================================================================================
Command Instruction:

	For newudpl
		./newudpl -i<ip_addr_ack>:<port_ack> -o<server_ip_address>:<listening_port> -L 50
	For tcpserver.py
		python3 tcpserver.py <file_name> <listening_port> <ip_addr_ack> <port_ack>

	For tcpclient.py
		python3 tcpserver.py test_file.s <udpl_addr> <udpl_port> <window_size> <port_ack>
	
	** When running tcpclient, make sure to pass in the window size in the multiple
		of 596 for the best performance.

		packet # | window_size
		---------|------------
			1	 |	  596	
			2	 |	  1192
			3 	 |	  1788
			4 	 |	  2384
			5 	 |	  2980
			6 	 |	  3576
			7 	 |	  4172
			8 	 |	  4768
			9 	 |	  5364
			10 	 |	  5960
		
	** It is better to use larger window size to have a faster result. Especially when
		newudpl is testing for more options, it would be advisable to use window size of
		at least 4172.
	
	** newudpl must be started newly for each transmission. If not, there is a possibility
		that tcpserver.py hangs and incorrectly wait for more packets.

	ex)
	newudpl command:
		./newudpl -ilocalhost:10006 -olocalhost:10007 -L 50
	tcpserver command:
		python3 tcpserver.py recieved_file.s 10007 127.0.0.1 10006
	tcpclient command:
		python3 tcpserver.py test_file.txt 127.0.0.1 41192 5960 10006

==========================================================================================
Features & Bugs:

	tcpclient will terminate with the print statement "All packets transmitted to server"
		when all ACK signals are received from the server.
	tcpserver will terminate with the print statement "Written all data to <file>" when
		it finished writting all received data.

	Both should be able to deal with corrupted bit that can be detected by checksum,
		out of order packet, and loss of packets. The server will not be able to detect
		the corrupted bit that cannot be detected with checksum.
	
	If newudpl is not started newly for each transmission, there is a possiblity that
		tcpserver.py program hangs even after tcpclient.py terminates. In this case, the
		file written by tcpserver.py will not be accurate.
	When tcpserver.py hangs, the programs should be ran again with new newudpl.

==========================================================================================