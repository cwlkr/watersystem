var socket = io();
var current_pump_status;

socket.on('connect', function() {
   socket.emit('my event', {data: 'I\'m connected!'});
});

socket.on('updated_pump_state', function(x){
	$("#resBtnHere").html(x.toString());
        current_pump_status = x;
})

socket.on('waterlevel_update', function(x) {
  handle_waterlvl_event(x)
});

$.get("/get_pump_status", //, async=false,
          function(x) {
          $("#resBtnHere").html(x.toString());
          current_pump_status = x
    }
   )

function handle_waterlvl_event(has_water){
  if ((!has_water) && (current_pump_status==false)){
    $("#waterlvl_message").css("display", "block");
    $("#my_button").attr('disabled','disabled');
   }
  else {
    $("#waterlvl_message").css("display", "none");
    $("#my_button").removeAttr('disabled');
  }
}

$.get("get_waterlvl", function(x){
   handle_waterlvl_event(x);
   }
 )

var cron_jobs;
$.get("/cron_jobs",
    function(x) {
          cron_jobs = x;
          render_cron_schedule(x);
    }
   )
   
socket.on('cron_job_update', function(x) {
          cron_jobs = x;
          render_cron_schedule(x);
  });


function render_cron_schedule(schedule){
    var table_list = ["<tr><th>active</th> <th>cron timeing</th> <th>duration</th></tr>"];
    // create tables
    // add headers?
    // add on change for checkboxes!!
    for (const [key, entry] of Object.entries(schedule)) {
  	table_list.push(`<tr> <td>      
      <input type="checkbox" id="active_table_${key}" name="active_${key}" value="active_${key}" ${entry.active ?  'checked': ''}>
      </td> <td> ${entry.minute} ${entry.hour} ${entry.dom} ${entry.mon} ${entry.dow}</td> <td>${entry.duration}</td> <td> <input type="button" id="edit_job_${key}" value="edit"> </td> <td> <input type="button" id="delete_job_${key}" value="delete"></td></tr>`)
    }
    $('#schedule_table').html(table_list.join(''));
    $('[id^=edit]').click(function(event){
    var form_idx = event.target.id.split(/[_]+/).pop();
    var current_job = schedule[form_idx];
    console.log(current_job)
    $("#job_input_form_div").css('display', 'block');
    $("#add_job_button").css('display', 'none');
    $("#submit_form").attr("value", 'save changes')
    $("#row_index").attr("value", form_idx)
    $("#duration").attr("value", current_job.duration)
    $("#active_").prop("checked", current_job.active)
    $("#m").attr("value", current_job.minute)
    $("#h").attr("value", current_job.hour)
    $("#dom").attr("value", current_job.dom)
    $("#mon").attr("value", current_job.mon)
    $("#dow").attr("value", current_job.dow)
  }
  )
    $('[id^=delete]').click(function(event){
      var form_idx = event.target.id.split(/[_]+/).pop();
      var current_job = schedule[form_idx];
      // ask for confirmation
      // if confirmation then send post request to server to delete entry.
  }
  )
  $('[id^=active_table]').on('change', function(event){
      var form_idx = event.target.id.split(/[_]+/).pop();
      var data = {idx:form_idx, checked: $("#" + event.target.id).prop('checked')}
      $.post('/change_job_active', data)
    })
}

var current_position=0;
var show_length = 50;
var log_data;

function renderTable(pos, n_elem, x){
  var current_selection = x.slice(pos, pos+n_elem);
  document.getElementById('logger_list').innerHTML = current_selection.map((k) => {
    return `<tr> <td> ${ k } </td></tr>`;
  }).join('');
}

function renderNext(x) {
  current_position = current_position+show_length
  renderTable(current_position, show_length, x)
  console.log(current_position)
  if (current_position >= show_length){
    document.getElementById("prev_bttn").style.display = "block";
  }
  if (current_position + show_length > log_data.length){
    document.getElementById("next_bttn").style.display = "none";
  }
};

// boundary conditions are not true yet!!
function renderPrev(array_) {
  current_position = current_position-show_length
  console.log(current_position)
  renderTable(current_position, show_length, array_)
  if (current_position == 0){
    document.getElementById("prev_bttn").style.display = "none";
  }
  if (current_position + show_length < log_data.length){
    document.getElementById("next_bttn").style.display = "block	";
  }
};

$("#next_bttn").click(function(){
    renderNext(log_data);
    }
  );

$("#prev_bttn").click(function(){
    renderPrev(log_data);
    }
  );

$("#add_job_button").click(function(){
  $("#job_input_form_div").css('display', 'block');
  $(this).css('display', 'none');
}
)

$("#cancel_form").click(function(){
  $("#job_input_form_div").css('display', 'none')
  $("#add_job_button").css('display', 'block');
  $("#submit_form").attr("value", 'submit');
  $("#job_input_form").find("input[type=text], textarea").attr("value", "");
  $("#job_input_form").trigger('reset')
  $("#row_index").attr("value", 'new');
  $("#warning_label").css('display', 'none');
}
)

$("#job_input_form").submit(function(e){

  $.post("/add_cron_job", $(this).serialize(), function(x){
    if (x == 'succesfull'){
      $("#job_input_form_div").css('display', 'none')
      $("#add_job_button").css('display', 'block');
      $("#submit_form").attr("value", 'submit');
      $("#job_input_form").find("input[type=text], textarea").attr("value", "");
      $("#job_input_form").trigger('reset')
      $("#row_index").attr("value", 'new');
      $("#warning_label").css('display', 'none');
    }
    else{
      $("#warning_label").css('display', 'block');
    }
  });
    // send post to server
    // if done/ a) reset form/ b) close form c) show added sucessfully? d) update the cronjob table.
  e.preventDefault();
})


$.get("/get_log_data",
          function(x) {
          log_data=x;
          renderTable(0, show_length, x);
    }
   );

$("#my_button").click(function(){
    socket.emit('pump_switch_press');

    if(!current_pump_status)  // and pump status is false!
    {
        $("#ProgressBarPercentage").animate({width:"100%"}, 10000, function () { $(this).removeAttr('style');}) 
    }
    else
    {
        $("#ProgressBarPercentage").stop()
        $("#ProgressBarPercentage").removeAttr('style');
    }
    }
  );

function openTab(evt, cityName) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(cityName).style.display = "block";
  evt.currentTarget.className += " active";
}
