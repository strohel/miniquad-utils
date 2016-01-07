var types = ["motor", "cell", "prop", "esc", "session"];
var data = Object();
data.motor = 7;
data.cell = 3;
data.prop = 3;
data.esc = 7;
data.session = 3;

var measurements = [
    [1, 1, 1, 1, 1],
    [2, 2, 2, 2, 2],
    [4, 2, 2, 4, 2],
];

function toggle(type, id) {
    data[type] ^= id;

    update_states();
}

var measurement_index = {
    motor: 0,
    cell: 1,
    prop: 2,
    esc: 3,
    session: 4
};
function get_measurement_count(type, id) {
    var index = measurement_index[type];
    function measurement_available(measurement) {
        return (data.motor & measurement[0])
            && (data.cell & measurement[1])
            && (data.prop & measurement[2])
            && (data.esc & measurement[3])
            && (data.session & measurement[4])
    }

    var count = 0;
    console.log("get_measurement_count(type="+type+", id="+id+"): index="+index);
    $.each(measurements, function(i, measurement) {
        if (measurement[index] == id && measurement_available(measurement))
            count++;
    });
    return count;
}

function update_states() {
    $.each(types, function(i, type) {
        var elements = $('#' + type + '-list').children("button");
        elements.each(function(i, element) {
            var id = 1 << i;
            var je = $(element);

            if (data[type] & id)
                je.addClass('active')
            else
                je.removeClass('active')
            je.children("span").html(get_measurement_count(type, id));
        });
    });
}

function add_events() {
    $.each(types, function(i, type) {
        var elements = $('#' + type + '-list').children("button");
        elements.each(function(i, element) {
            var id = 1 << i;
            element.onclick = function() { toggle(type, id); };
        });
    });
}

add_events();
update_states();
