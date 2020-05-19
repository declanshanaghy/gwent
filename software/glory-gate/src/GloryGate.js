import React, {Component} from 'react'
import Card from './Card'

const URL = 'ws://192.168.1.185:8888';
// const URL = 'ws://localhost:8888';

class GloryGate extends Component {
    ws = new WebSocket(URL);

    constructor(props) {
        super(props);
        this.state = {
            status: {
                code: 0,
                reading_card: false
            },
            card: null,
            connected: false,
        };
    }

    componentDidMount() {
        this.ws.onopen = () => {
            // on connecting, do nothing but log it to the console
            console.log('connected')
            this.setState({
                connected: true,
            })
        };

        this.ws.onmessage = evt => {
            const message = JSON.parse(evt.data);
            switch (message.action) {
                case 'status':
                    this.onStatus(message.payload);
                    break;
                case 'card_read':
                    this.onCardRead(message.payload);
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

    onStatus = status => {
        this.setState({
            status: status,
        })
        console.log(`Completed onStatus: reading_card=${this.state.status.reading_card}`);
    };

    onCardRead = card => {
        this.setState({
            card: card,
        })
        console.log(`Completed onCardRead: id=${this.state.card.id}`);

        this.disableCardReader();
    };

    isReadingCard = () => {
        return this.state.status.reading_card;
    }

    disableCardReader = () => {
        if ( this.isReadingCard() ) {
            this.toggleCardReaderState()
        }
    };

    enableCardReader = () => {
        if ( !this.isReadingCard() ) {
            this.toggleCardReaderState()
        }
    };

    toggleCardReaderState = () => {
        const newState = !this.state.status.reading_card
        console.log(`toggleCardReaderState: ${newState}`);
        const message = {
            action: 'set_state',
            payload: {
                'reading_card': newState,
            }
        };
        this.ws.send(JSON.stringify(message));
    };

    onSaveCard = (card) => {
        console.log('About to save card');
        console.log(this.state.card);
        const message = {
            action: 'save_card',
            payload: card,
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
                    card={this.state.card}
                    onSaveCard={(card) => this.onSaveCard(card)}
                />
            </div>
        )
    }
}

export default GloryGate
