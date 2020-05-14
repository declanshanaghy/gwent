import React, {Component} from 'react'
import PropTypes from 'prop-types'

class Card extends Component {
    static propTypes = {
        onSubmit: PropTypes.func.isRequired,
    };
    state = {
        id: '',
        name: '',
        faction: '',
    };

    render() {
        return (
            <form
                action="."
                onSubmit={e => {
                    e.preventDefault();
                    this.props.onSubmit(this.state.name, this.state.faction);
                }}
            >
                <div>
                    <label htmlFor="name">Name:</label>
                    <input
                        type="text"
                        placeholder={'Enter name...'}
                        value={this.state.name}
                        onChange={e => this.setState({message: e.target.value})}
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

export default Card
