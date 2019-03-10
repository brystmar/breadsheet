// add an event listener for the selection box
document.getElementById("solve_for_start").addEventListener("change", sfToggle);

function sfToggle() {
    var box = document.getElementById("solve_for_start");
    var sdate = document.getElementById("start_date");
    var stime = document.getElementById("start_time");
    var fdate = document.getElementById("finish_date");
    var ftime = document.getElementById("finish_time");
    var s_now = document.getElementById("start_now");
    var f_now = document.getElementById("finish_now");

    if (box.value === "1") {
        sdate.disabled = true
        stime.disabled = true
        fdate.disabled = false
        ftime.disabled = false
        s_now.disabled = true
        f_now.disabled = false
        }
    else {
        sdate.disabled = false
        stime.disabled = false
        fdate.disabled = true
        ftime.disabled = true
        s_now.disabled = false
        f_now.disabled = true
    }
}

function calcTime() {


}

function addStep() {
    var div_ask_add_step = document.getElementById("ask_add_step");
    var div_add_step = document.getElementById("add_step");

    document.getElementById("ask_add_step").style.display = "none";
    document.getElementById("add_step").style.display = "block";
}

function clearFields() {
    document.getElementById("ingredients_input").value = "";
    document.getElementById("directions_input").value = "";
    document.getElementById("ingredients_output").value = "";
    document.getElementById("directions_output").value = "";
    document.getElementById("ingredients_input").focus();
    document.getElementById("convert_text_flash_msg").style.display = "none";
}

function startNow() {
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
}

function finishNow() {
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
}
