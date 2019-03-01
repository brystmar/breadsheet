/*
// add an event listener for the selection box
document.getElementById("solve_for_start")[0].addEventListener('change', ShowHide());

function ShowHide(){
    if (document.getElementById("solve_for_start").val() === "S") {
        document.getElementById("start_time_text").hide();
        document.getElementById("start_time_controls").hide();
        document.getElementById("finish_time_text").show();
        document.getElementById("finish_time_controls").show();
        }

    else {
        document.getElementById("start_time_text").show();
        document.getElementById("start_time_controls").show();
        document.getElementById("finish_time_text").hide();
        document.getElementById("finish_time_controls").hide();
        }
    }*/
/*

$(document).ready(function () {
    toggleFields(); // call this first so we start out with the correct visibility depending on the selected form values
    // this will call our toggleFields function every time the selection value of our other field changes
    $("#solve_for_start").change(function () {
        toggleFields();
    });

});
// this toggles the visibility of other server
function toggleFields() {
    if ($("#solve_for_start").val() === "S")
        $("#otherServer").show();
    else
        $("#otherServer").hide();
}*/

/*$('#solve_for_start').on('change',function(){
    if( $(this).val()==="S"){
    $("#start_time_text").show()
    }
    else{
    $("#start_time_text").hide()
    }
});*/

/*
jQuery('select[id=solve_for_start]').change(function(){
        var fieldsetName = $(this).val();
        $('fieldset').hide().filter('#' + fieldsetName).show();
    });

    // We need to hide all fieldsets except the first:
    $('fieldset').hide().filter('#start_time_controls1').show();
*/


function ClearFields() {
    document.getElementById("ingredients_input").value = "";
    document.getElementById("directions_input").value = "";
    document.getElementById("ingredients_output").value = "";
    document.getElementById("directions_output").value = "";
    document.getElementById("ingredients_input").focus();
    document.getElementById("convert_text_flash_msg").style.display = "none";
    };

function StartNow() {
    var date = new Date();
    var day = date.getDate();
    var month = date.getMonth() + 1;
    var year = date.getFullYear();

    if (month < 10) month = "0" + month;
    if (day < 10) day = "0" + day;
    var today = year + "-" + month + "-" + day;

    document.getElementById('start_date').value = today;

    var hour = date.getHours();
    var minute = date.getMinutes();
    var time = hour + ":" + minute;

    document.getElementById('start_time').value = time;
    };

function FinishNow() {
    var date = new Date();
    var day = date.getDate();
    var month = date.getMonth() + 1;
    var year = date.getFullYear();

    if (month < 10) month = "0" + month;
    if (day < 10) day = "0" + day;
    var today = year + "-" + month + "-" + day;

    document.getElementById('finish_date').value = today;

    var hour = date.getHours();
    var minute = date.getMinutes();
    var time = hour + ":" + minute;

    document.getElementById('finish_time').value = time;
    };
