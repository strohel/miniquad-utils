var types = ["motor", "cell", "prop", "esc", "author"];

// filled in in initialize()
var measurements;
var data;
var all_data;

function toggle(type, id) {
    data[type] ^= id;
    update_states();
}

function activate_all(type) {
    data[type] = all_data[type];
    update_states();
}

function group_by(type) {
    data[type] = 0;
    update_states();
}

var measurement_index = {
    motor: 0,
    cell: 1,
    prop: 2,
    esc: 3,
    author: 4
};
function get_measurement_count(type, id) {
    var index = measurement_index[type];

    // pretend this type-id combination is active
    var mend_data = $.extend({}, data);
    mend_data[type] |= id;

    function measurement_available(measurement) {
        return (mend_data.motor == 0 || mend_data.motor & measurement[0])
            && (mend_data.cell == 0 || mend_data.cell & measurement[1])
            && (mend_data.prop == 0 || mend_data.prop & measurement[2])
            && (mend_data.esc == 0 || mend_data.esc & measurement[3])
            && (mend_data.author == 0 || mend_data.author & measurement[4])
    }

    var count = 0;
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

            var count = get_measurement_count(type, id);
            if (data[type] & id) {
                if (count == 0)
                    je.removeClass('active').addClass('list-group-item-info');
                else
                    je.addClass('active').removeClass('list-group-item-info');
            } else {
                je.removeClass('active').removeClass('list-group-item-info');
                // number of woud-be-added items is shown in this case, unless group-by is active
                if (data[type] != 0)
                    count = "+ "+count;
            }

            je.children("span").html(count);
        });

        var jall_btn = $('#'+type+"-all");
        if (data[type] == all_data[type])
            jall_btn.addClass('active');
        else
            jall_btn.removeClass('active');

        var jgroup_btn = $('#'+type+"-group");
        if (data[type] == 0)
            jgroup_btn.addClass('btn-primary');
        else
            jgroup_btn.removeClass('btn-primary');

    });
}

function initialize() {
    $.getJSON('data.json', initialize_phase_two);
}

function initialize_phase_two(json) {
    measurements = json.measurements;
    var items = json.items;

    all_data = Object();
    $.each(types, function(i, type) {
        var button_list = $('#' + type + '-list');
        $.each(items[type], function(i, name) {
            var id = 1 << i;
            all_data[type] |= id
            var element = $('<button type="button" class="list-group-item">'+name+' <span class="badge">?</span></button>');
            button_list.append(element);
            element.click(function() { toggle(type, id); });
        });

        var extra_buttons = $('<div class="btn-group btn-group-justified">'
            + '  <div class="btn-group"><button id="'+type+'-all" type="button" class="btn btn-default">All</button></div>'
            + '  <div class="btn-group"><button id="'+type+'-group" type="button" class="btn">Group By</button></div>'
            + '</div>');
        button_list.after(extra_buttons);
        $('#'+type+"-all").click(function() { activate_all(type); });
        $('#'+type+"-group").click(function() { group_by(type); });
    });

    data = $.extend({}, all_data);
    console.log(all_data);
    console.log(data);
    update_states();
}

initialize();
