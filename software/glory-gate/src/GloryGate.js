import React, {Component} from 'react'
import Card from './Card'

const URL = 'ws://192.168.1.185:8888';
// const URL = 'ws://localhost:8888';

class GloryGate extends Component {
    state = {
        status: {
            code: 0,
            reading_card: false
        },
        card: null,
        connected: false,
    };

    ws = new WebSocket(URL);

    componentDidMount() {
        this.ws.onopen = () => {
            // on connecting, do nothing but log it to the console
            console.log('connected')
            this.setState({
                connected: true,
            })
        };

        this.onStatus = status => {
            console.log('Handled status update');
            this.setState({
                status: status,
            })
            console.log(this.state.status);
        };

        this.ws.onmessage = evt => {
            const message = JSON.parse(evt.data);
            switch (message.action) {
            case 'status':
                this.onStatus(message.payload);
                break;
            default:
                console.log(`Unhandled message action: ${message.action}`);
            }
        };

        this.ws.onclose = () => {
            this.setState({
                connected: false,
            })
            console.log('disconnected');
            // automatically try to reconnect on connection loss
            this.setState({
                ws: new WebSocket(URL),
            })
        }
    }

    toggleCardReaderState = () => {
        const message = {
            action: 'set_state',
            payload: {
                'reading_card': !this.state.status.reading_card,
            }
        };
        this.ws.send(JSON.stringify(message));
    };

    saveCard = (id, name, faction) => {
        // on submitting the ChatInput form, send the message, add it to the list and reset the input
        const message = {
            action: 'card_save',
            payload: {
                id: id,
                details: {
                    name: name,
                    faction: faction
                }
            }
        };
        this.ws.send(JSON.stringify(message));
    };

    render() {
        return (
            <div>
                <div>
                    <label htmlFor="connected">
                        Connected?
                    </label>
                    <span> {(this.state.connected) ? 'Yes' : 'No'}</span>
                </div>
                <div>
                    <label htmlFor="reading_card">
                        Reading Card?
                    </label>
                    <span> {(this.state.status.reading_card) ? 'Yes' : 'No'}</span>
                </div>
                <p/><p/>
                <div>
                    <button className="CardReader" onClick={() => this.toggleCardReaderState()}>
                        {(this.state.status.reading_card) ? 'Stop Reading' : 'Start Reading'}
                    </button>
                </div>
                <p/><p/>
                <Card
                    onSubmit={(id, name, faction) => this.saveCard(id, name, faction)}
                />
            </div>
        )
    }
}

export default GloryGate
