/**
 * @title How long do things tend to take?
 * @description Cloze norming experiment for temporal-modifier preferences.
 * @version 0.14.3
 *
 * @assets assets/
 */

import "../styles/main.scss";

import FullscreenPlugin from "@jspsych/plugin-fullscreen";
import jsPsychSurveyText from '@jspsych/plugin-survey-text';
import jsPsychClozeDropdown from './plugin-cloze-dropdown';
import { initJsPsych } from "jspsych";

// Turn debug mode on when testing locally.
const debugMode = true;

// Define the conditions.
const conditions = [
  "contentful_episodic",
  "bleached_episodic",
  "contentful_generic",
  "bleached_generic",
  "templatic_episodic"
];

// Load the items.
const items = require('./cloze-items.json');

// Compute the number of lists for each condition.
const numLists = {};

for (var i = 0; i < conditions.length; i++) {
  numLists[conditions[i]] = items[conditions[i]].length;
} 

// Define the number of participants per list for each condition.
const numParticipantsPerList = {
  "contentful_episodic": 12, // target is 10 
  "bleached_episodic": 22, // target is 20
  "contentful_generic": 12, // target is 10
  "bleached_generic": 22, // target is 20
  "templatic_episodic": 42 // target is 40
};

// Define the instructions to be used for each condition.
const instructions = {
  "contentful_episodic": `
  <p class="instructions">
    In this study, we are interested in how long things tend to take. To investigate this question, we will give you sentences with blanks in them and ask you to fill in those blanks with the values that you think are most natural using the dropdowns we provide.
  </p>
  
  <p class="instructions">
      For example, you might receive the following sentence:
  </p>
  
  <p class="example">The child ate the sandwich
      <select id="clozeDropdownBlank0" name="clozeDropdownBlank0" required="">
          <option selected="" disabled="" value="">in/for</option>
          <option value="in">in</option>
          <option value="for">for</option>
      </select>
      <select id="clozeDropdownBlank1" name="clozeDropdownBlank1" required="">
          <option selected="" disabled="" value="">NUM</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
          <option value="5">5</option>
          <option value="10">10</option>
          <option value="15">15</option>
          <option value="20">20</option>
          <option value="25">25</option>
          <option value="30">30</option>
          <option value="35">35</option>
          <option value="40">40</option>
          <option value="45">45</option>
          <option value="50">50</option>
          <option value="55">55</option>
          <option value="60">60</option>
          <option value="65">65</option>
          <option value="70">70</option>
          <option value="75">75</option>
          <option value="80">80</option>
          <option value="85">85</option>
          <option value="90">90</option>
          <option value="95">95</option>
          <option value="100">100</option>
      </select>
      <select id="clozeDropdownBlank2" name="clozeDropdownBlank2" required="">
          <option selected="" disabled="" value="">DURATION</option>
          <option value="milliseconds">milliseconds</option>
          <option value="seconds">seconds</option>
          <option value="minutes">minutes</option>
          <option value="hours">hours</option>
          <option value="days">days</option>
          <option value="weeks">weeks</option>
          <option value="months">months</option>
          <option value="years">years</option>
          <option value="decades">decades</option>
          <option value="centuries">centuries</option>
          <option value="millenia">millenia</option>
      </select>.
  </p>
  
  <p class="instructions">
      A natural way to complete this sentence might be <i>in 5 minutes</i>, which you would indicate by selecting <i>in</i> from the first dropdown, <i>5</i> from the second, and <i>minutes</i> from the third.
  </p>
  
  <p class="instructions">
      Alternatively, you might consider <i>in 30 seconds</i> or <i>in 1 hour</i> more natural, depending on how long you think it generally takes children to eat sandwiches. In cases like this, where multiple options are natural, choose the one you think is most natural.
  </p>
  
  <p class="instructions">
      This research is being carried out by Dr. Aaron White at the University of Rochester. You can read more about the study <a target=”_blank” href="http://factslab.io/information_sheet_021523.pdf">here</a>. Upon clicking continue, you will enter fullscreen mode.
  </p>
  `,
  "bleached_episodic": `
  <p class="instructions">
    In this study, we are interested in how long things tend to take. To investigate this question, we will give you sentences with blanks in them and ask you to fill in those blanks with the values that you think are most natural using the dropdowns we provide.
  </p>
  
  <p class="instructions">
      For example, you might receive the following sentence:
  </p>
  
  <p class="example">The person ate the thing 
      <select id="clozeDropdownBlank0" name="clozeDropdownBlank0" required="">
          <option selected="" disabled="" value="">in/for</option>
          <option value="in">in</option>
          <option value="for">for</option>
      </select>
      <select id="clozeDropdownBlank1" name="clozeDropdownBlank1" required="">
          <option selected="" disabled="" value="">NUM</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
          <option value="5">5</option>
          <option value="10">10</option>
          <option value="15">15</option>
          <option value="20">20</option>
          <option value="25">25</option>
          <option value="30">30</option>
          <option value="35">35</option>
          <option value="40">40</option>
          <option value="45">45</option>
          <option value="50">50</option>
          <option value="55">55</option>
          <option value="60">60</option>
          <option value="65">65</option>
          <option value="70">70</option>
          <option value="75">75</option>
          <option value="80">80</option>
          <option value="85">85</option>
          <option value="90">90</option>
          <option value="95">95</option>
          <option value="100">100</option>
      </select>
      <select id="clozeDropdownBlank2" name="clozeDropdownBlank2" required="">
          <option selected="" disabled="" value="">DURATION</option>
          <option value="milliseconds">milliseconds</option>
          <option value="seconds">seconds</option>
          <option value="minutes">minutes</option>
          <option value="hours">hours</option>
          <option value="days">days</option>
          <option value="weeks">weeks</option>
          <option value="months">months</option>
          <option value="years">years</option>
          <option value="decades">decades</option>
          <option value="centuries">centuries</option>
          <option value="millenia">millenia</option>
      </select>.
  </p>
  
  <p class="instructions">
      A natural way to complete this sentence might be <i>in 5 minutes</i>, which you would indicate by selecting <i>in</i> from the first dropdown, <i>5</i> from the second, and <i>minutes</i> from the third.
  </p>
  
  <p class="instructions">
      Alternatively, you might consider <i>in 30 seconds</i> or <i>in 1 hour</i> more natural, depending on how long you think it generally takes people to eat things. In cases like this, where multiple options are natural, choose the one you think is most natural.
  </p>
  
  <p class="instructions">
      This research is being carried out by Dr. Aaron White at the University of Rochester. You can read more about the study <a target=”_blank” href="http://factslab.io/information_sheet_021523.pdf">here</a>. Upon clicking continue, you will enter fullscreen mode.
  </p>
  `,
  "contentful_generic": `
  <p class="instructions">
    In this study, we are interested in how long things tend to take. To investigate this question, we will give you sentences with blanks in them and ask you to fill in those blanks with the values that you think are most natural using the dropdowns we provide.
  </p>
  
  <p class="instructions">
      For example, you might receive the following sentence:
  </p>
  
  <p class="example">Children eat sandwiches 
      <select id="clozeDropdownBlank0" name="clozeDropdownBlank0" required="">
          <option selected="" disabled="" value="">in/for</option>
          <option value="in">in</option>
          <option value="for">for</option>
      </select>
      <select id="clozeDropdownBlank2" name="clozeDropdownBlank2" required="">
          <option selected="" disabled="" value="">DURATION</option>
          <option value="milliseconds">milliseconds</option>
          <option value="seconds">seconds</option>
          <option value="minutes">minutes</option>
          <option value="hours">hours</option>
          <option value="days">days</option>
          <option value="weeks">weeks</option>
          <option value="months">months</option>
          <option value="years">years</option>
          <option value="decades">decades</option>
          <option value="centuries">centuries</option>
          <option value="millenia">millenia</option>
      </select>.
  </p>
  
  <p class="instructions">
      A natural way to complete this sentence might be <i>in minutes</i>, which you would indicate by selecting <i>in</i> from the first dropdown and <i>minutes</i> from the second.
  </p>
  
  <p class="instructions">
      Alternatively, you might consider <i>in seconds</i> or <i>in hours</i> more natural, depending on how long you think it generally takes children to eat sandwiches. In cases like this, where multiple options are natural, choose the one you think is most natural.
  </p>
  
  <p class="instructions">
      This research is being carried out by Dr. Aaron White at the University of Rochester. You can read more about the study <a target=”_blank” href="http://factslab.io/information_sheet_021523.pdf">here</a>. Upon clicking continue, you will enter fullscreen mode.
  </p>
  `,
  "bleached_generic": `
  <p class="instructions">
    In this study, we are interested in how long things tend to take. To investigate this question, we will give you sentences with blanks in them and ask you to fill in those blanks with the values that you think are most natural using the dropdowns we provide.
  </p>
  
  <p class="instructions">
      For example, you might receive the following sentence:
  </p>
  
  <p class="example">People eat things 
      <select id="clozeDropdownBlank0" name="clozeDropdownBlank0" required="">
          <option selected="" disabled="" value="">in/for</option>
          <option value="in">in</option>
          <option value="for">for</option>
      </select>
      <select id="clozeDropdownBlank2" name="clozeDropdownBlank2" required="">
          <option selected="" disabled="" value="">DURATION</option>
          <option value="milliseconds">milliseconds</option>
          <option value="seconds">seconds</option>
          <option value="minutes">minutes</option>
          <option value="hours">hours</option>
          <option value="days">days</option>
          <option value="weeks">weeks</option>
          <option value="months">months</option>
          <option value="years">years</option>
          <option value="decades">decades</option>
          <option value="centuries">centuries</option>
          <option value="millenia">millenia</option>
      </select>.
  </p>
  
  <p class="instructions">
      A natural way to complete this sentence might be <i>in minutes</i>, which you would indicate by selecting <i>in</i> from the first dropdown and <i>minutes</i> from the second.
  </p>
  
  <p class="instructions">
      Alternatively, you might consider <i>in seconds</i> or <i>in hours</i> more natural, depending on how long you think it generally takes people to eat things. In cases like this, where multiple options are natural, choose the one you think is most natural.
  </p>
  
  <p class="instructions">
      This research is being carried out by Dr. Aaron White at the University of Rochester. You can read more about the study <a target=”_blank” href="http://factslab.io/information_sheet_021523.pdf">here</a>. Upon clicking continue, you will enter fullscreen mode.
  </p>
  `,
  "templatic_episodic": `
  <p class="instructions">
    In this study, we are interested in how long things tend to take. To investigate this question, we will give you sentences with blanks in them and ask you to fill in those blanks with the values that you think are most natural using the dropdowns we provide.
  </p>
  
  <p class="instructions">
      For example, you might receive the following sentence:
  </p>
  
  <p class="example">X ate Y
      <select id="clozeDropdownBlank0" name="clozeDropdownBlank0" required="">
          <option selected="" disabled="" value="">in/for</option>
          <option value="in">in</option>
          <option value="for">for</option>
      </select>
      <select id="clozeDropdownBlank1" name="clozeDropdownBlank1" required="">
          <option selected="" disabled="" value="">NUM</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
          <option value="5">5</option>
          <option value="10">10</option>
          <option value="15">15</option>
          <option value="20">20</option>
          <option value="25">25</option>
          <option value="30">30</option>
          <option value="35">35</option>
          <option value="40">40</option>
          <option value="45">45</option>
          <option value="50">50</option>
          <option value="55">55</option>
          <option value="60">60</option>
          <option value="65">65</option>
          <option value="70">70</option>
          <option value="75">75</option>
          <option value="80">80</option>
          <option value="85">85</option>
          <option value="90">90</option>
          <option value="95">95</option>
          <option value="100">100</option>
      </select>
      <select id="clozeDropdownBlank2" name="clozeDropdownBlank2" required="">
          <option selected="" disabled="" value="">DURATION</option>
          <option value="milliseconds">milliseconds</option>
          <option value="seconds">seconds</option>
          <option value="minutes">minutes</option>
          <option value="hours">hours</option>
          <option value="days">days</option>
          <option value="weeks">weeks</option>
          <option value="months">months</option>
          <option value="years">years</option>
          <option value="decades">decades</option>
          <option value="centuries">centuries</option>
          <option value="millenia">millenia</option>
      </select>.
  </p>
  
  <p class="instructions">
      A natural way to complete this sentence might be <i>in 5 minutes</i>, which you would indicate by selecting <i>in</i> from the first dropdown, <i>5</i> from the second, and <i>minutes</i> from the third.
  </p>
  
  <p class="instructions">
      Alternatively, you might consider <i>in 30 seconds</i> or <i>in 1 hour</i> more natural, depending on how long you think eating generally takes. In cases like this, where multiple options are natural, choose the one you think is most natural.
  </p>
  
  <p class="instructions">
      This research is being carried out by Dr. Aaron White at the University of Rochester. You can read more about the study <a target=”_blank” href="http://factslab.io/information_sheet_021523.pdf">here</a>. Upon clicking continue, you will enter fullscreen mode.
  </p>
  `
};

const preposition_choice = (state) => {
  return ["in", "for"];
};

const numeral_choice = (state) => {
  return [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", 
    "15", "20", "25", "30", "35", "40", "45", 
    "50", "55", "60", "65", "70", "75", "80",
    "85", "90", "95", "100", "200", "300", "400", "500",
    "600", "700", "800", "900", "1,000"
  ];
};

var duration_choice = (state) => {
  if (state.numeral == "1") {
    return [
      "millisecond",
      "second",
      "minute",
      "hour",
      "day",
      "week",
      "month",
      "year",
      "decade",
      "century",
      "millenium"
    ];
  } else {
    return [
      "milliseconds",
      "seconds",
      "minutes",
      "hours",
      "days",
      "weeks",
      "months",
      "years",
      "decades",
      "centuries",
      "millenia"
    ];
  }
};

// Initialize the JATOS assignment queue.
function initBatchConditions() {
  // Populate the queue only once.
  if (!jatos.batchSession.defined("/lists_to_run")) {    
    var lists_to_run = [];

    for (var i = 0; i < conditions.length; i++){
      for (var j = 0; j < numLists[conditions[i]]; j++) {
        for (var k = 0; k < numParticipantsPerList[conditions[i]]; k++) {
          lists_to_run.push(
            {
              "condition": conditions[i],
              "list_num": j
            }
          );
        }
      }
    }

    // Store the available assignments.
    jatos.batchSession.set("lists_to_run", lists_to_run)
      .fail(initBatchConditions); // Retry a failed write.
  }

  return true;
}

// Select the next assignment.
var getNextList;

if (debugMode) {
  // Use a fixed assignment in debug mode.
  getNextList = function() {
    return {
      "condition": "contentful_episodic",
      "list_num": 0
    }
  }
} else {
  // Draw an assignment from the JATOS queue.
  getNextList = function() {
    // Read the remaining assignments.
    var lists_to_run = jatos.batchSession.get("lists_to_run");
    
    // Stop when the queue is empty.
    if (lists_to_run.length == 0) {
      alert("Error: max number of workers reached.");
      throw "Max number of workers reached.";
    }
    
    // Choose a remaining assignment.
    var randomIndex = Math.floor(Math.random() * lists_to_run.length);
    var randomList = lists_to_run[randomIndex];
    
    // Remove the chosen assignment from the queue.
    lists_to_run.splice(randomIndex, 1);
    
    // Persist the remaining assignments.
    jatos.batchSession.set("lists_to_run", lists_to_run).fail(
      function () {
        randomList = getNextList(); // Retry a failed write.
      }
    );
    
    return randomList;
  }
}


/**
 * jsPsych Builder calls this function to run the experiment.
 *
 * @type {import("jspsych-builder").RunFunction}
 */
export async function run({ assetPaths, input = {}, environment, title, version }) {
  // Initialize jspsych.
  const jsPsych = initJsPsych({
    show_progress_bar: true
  });

  if (!debugMode) {
    // Initialize the batch session if necessary.
    var initComplete = await initBatchConditions();

    jsPsych.data.addProperties(
      jatos.urlQueryParameters
    );
  }

  // Get the condition and list number.
  var currList = getNextList();

  // Create the timeline.
  const timeline = [];

  // Add the instructions page to the timeline.
  timeline.push({
    type: FullscreenPlugin,
    message: instructions[currList.condition],
    fullscreen_mode: true,
  });

  var blanks;

  if (currList.condition === "contentful_generic" || currList.condition === "bleached_generic") {
    // In the generic conditions, we don't ask for a numeral.
    blanks = [
      {
        name: "preposition",
        choices: preposition_choice,
        placeholder: "in/for"
      },
      {
        name: "duration",
        choices: duration_choice,
        placeholder: "DURATION"
      }
    ];
  } else {
    // In the episodic conditions, we ask for a numeral.
    blanks = [
      {
        name: "preposition",
        choices: preposition_choice,
        placeholder: "in/for"
      },
      {
        name: "numeral",
        choices: numeral_choice,
        placeholder: "NUM"
      },
      {
        name: "duration",
        choices: duration_choice,
        placeholder: "DURATION"
      }
    ];
  }

  // Randomly shuffle the items.
  const items_shuffled = jsPsych.randomization.shuffle(
    items[currList.condition][currList.list_num]
  );

  // Add the trials to the timeline.
  for (let i = 0; i < items_shuffled.length; i++) {
    let cloze_trial = {
      type: jsPsychClozeDropdown,
      "text": items_shuffled[i],
      "blanks": blanks,
      "mistake_fn": function (){ alert("You have not filled one of the blanks.") }
    };
    timeline.push(cloze_trial);
  }
  
  // Add the comments box to the timeline.
  timeline.push({
    type: jsPsychSurveyText,
    questions: [
      {prompt: '<p>Please provide any feedback on the experiment.</p>', rows: 5}
    ]
  });

  await jsPsych.run(timeline);

  // Return the instance so jsPsych Builder can access the results.
  return jsPsych;
}
