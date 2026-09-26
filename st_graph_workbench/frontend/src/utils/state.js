class StateManager {
    constructor() {
        this.state = {
            selection: {
                selected: null,
                lastSelected: null,
            },
            style: {
                theme: "light",
                custom_style: [],
            },
            layout: null,
            lastExpanded: false,
            expansionBadgesVisible: true,
            selectionDetailsVisible: true,
            selectionDetailsOption: null,
            connectedDragEnabled: false,
            connectedDragDepth: 1,
            connectedDragOption: null,
            toolbarMinimized: false,
            toolbarSearchExpanded: false,
            toolbarOption: null,
        };
        this.observers = {
            selection: [],
            style: [],
            layout: [],
            lastExpanded: [],
            expansionBadgesVisible: [],
            selectionDetailsVisible: [],
            selectionDetailsOption: [],
            connectedDragEnabled: [],
            connectedDragDepth: [],
            connectedDragOption: [],
            toolbarMinimized: [],
            toolbarSearchExpanded: [],
            toolbarOption: [],
        };
    }
    getState(name) {
        return this.state[name];
    }
    updateState(name, value) {
        this.state[name] = value;
        this.notify(name);
    }
    subscribe(name, observer) {
        this.observers[name].push(observer);
    }
    notify(name) {
        this.observers[name].forEach((ob) => {
            ob(this.state[name]);
        });
    }
}

function createState() {
    return new StateManager();
}

export { createState, StateManager };
