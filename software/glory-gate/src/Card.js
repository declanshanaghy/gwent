import React, {Component} from 'react'
import PropTypes from 'prop-types'

class Card extends Component {
    static propTypes = {
        onSaveCard: PropTypes.func.isRequired,
        card: PropTypes.object,
    };
    constructor(props) {
        super(props);
        this.state = Card.newState();
    }

    static getDerivedStateFromProps(nextProps, prevState) {
        if ( nextProps.card != null ) {
            const card = nextProps.card;
            const details = card.details;
            console.log(`recieved card id=${card.id}, details=${details}`);
            return {
                card: card,
                id: card.id,
                name: details.name,
                faction: details.faction,
            };
        } else {
            console.log(`recieved null card`);
            return Card.newState()
        }
    }

    static newState() {
        return {
            card: null,
        };
    }

    componentDidMount() {
        console.log(`card componentDidMount`);
    }

    render() {
        if ( this.state.card == null ) {
            return (
                <p>Scan a card</p>
            )
        } else {
            return (
                <form
                    action="."
                    onSubmit={e => {
                        e.preventDefault();
                        const card = {
                            id: this.state.id,
                            details: {
                                name: this.state.name,
                                faction: this.state.faction,
                            },
                        }
                        this.props.onSaveCard(card);
                    }}
                >
                    <div>
                        <label htmlFor="id">ID:</label>
                        <label>{this.state.id}</label>
                    </div>
                    <div>
                        <label htmlFor="name">Name:</label>
                        <input
                            type="text"
                            placeholder={'Enter name...'}
                            value={this.state.name}
                            onChange={e => this.setState({name: e.target.value})}
                        />
                    </div>
                    <div>
                        <label htmlFor="faction">Faction:</label>
                        <input
                            type="text"
                            placeholder={'Enter faction...'}
                            value={this.state.faction}
                            onChange={e => this.setState({faction: e.target.value})}
                        />
                    </div>
                    <div>
                        <input type="submit" value={'Save'}/>
                    </div>
                </form>
            )
        }
    }
}

export default Card
