function getContainerIds() {
    const containerElements = document.getElementsByClassName('container');
    const containerIds = [];

    for (let i = 0; i < containerElements.length; i++) {
        const containerId = containerElements[i].id;
        if (containerId) {
            containerIds.push(containerId);
        }
    }

    return containerIds;
}

function mapArrayToLookup(array,lookup) {
	return array.map(item => {
	    if( lookup.hasOwnProperty(item)) {
	      return(lookup[item]) 
	    } else { 
	      return(item)
	    };  
	}).flat();
	}; 


$(document).ready(function () {
    const urlParams = new URLSearchParams(window.location.search);
    
    const hideIds = urlParams.get('hide');
    const showIds = urlParams.get('show');

    const hideArray = hideIds ? hideIds.split(',') : [];
    const showArray = showIds ? showIds.split(',') : [];

    console.log(hideArray);

    if (hideArray.length > 0) {

        const hideArrayFull = mapArrayToLookup(hideArray,bundles);

        hideArrayFull.forEach(id => {
            const div = document.getElementById(id);
            if (div) {
                div.style.display = 'none';
            }
        });
    }

    if (showArray.length > 0) {

        const showArrayFull = mapArrayToLookup(showArray,bundles);

        const allArray = getContainerIds();
        const combArray = allArray.filter(x => !showArrayFull.includes(x));

        combArray.forEach(id => {
            const div = document.getElementById(id);
            if (div) {
                div.style.display = 'none';
            }
        });
    }

    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

});