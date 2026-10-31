import { Client } from '@stomp/stompjs';
import WebSocket from 'ws';

Object.assign(global, { WebSocket });

const client = new Client({
    brokerURL: 'ws://localhost:8080/ws/alerts',
    onConnect: () => {
        console.log("Connected to STOMP");
        let count = 0;
        client.subscribe('/topic/alerts', message => {
            const result = JSON.parse(message.body);
            console.log(`[Alert] ${result.predictionClass} (${result.predictionLabel}) - Latency: ${result.latencyMs.toFixed(3)}ms - ID: ${result.message.canId}`);
            count++;
            if (count >= 10) {
                console.log("Received 10 messages. Disconnecting.");
                client.deactivate();
                process.exit(0);
            }
        });
    },
    onStompError: (frame) => {
        console.error('Broker reported error: ' + frame.headers['message']);
        console.error('Additional details: ' + frame.body);
    },
});

console.log("Connecting...");
client.activate();
