
function editChapterName(item){
  // dont click when edit is going on!
  var textAreas = document.getElementsByClassName("EditChapterTextArea")
  if (textAreas.length>0){
    return;
  }
  var EditChapterTextArea = document.createElement("textarea")
  var oldChapterName = item.textContent
  notebookName = document.getElementById("notebookName").textContent;
  EditChapterTextArea.className = "EditChapterTextArea"
  EditChapterTextArea.style.resize = "none"
  EditChapterTextArea.cols = "14"
  EditChapterTextArea.rows = "1"
  EditChapterTextArea.value = oldChapterName;
  item.textContent = null;
  EditChapterTextArea.onkeypress=function(){
    var key = window.event.keyCode;
    if (key === 13) {
      this.parentElement.textContent = this.value;
      tempNotebooks[notebookName][this.value] = tempNotebooks[notebookName][oldChapterName]
      delete tempNotebooks[notebookName][oldChapterName]
      if(this.value != oldChapterName){
         $.ajax({ type: "POST",
                  url: "http://"+window.location.hostname+":5000/notes",
                  data: {"rename":JSON.stringify({"type": "chapterName",
                                                  "noteBookName": notebookName,
                                                  "oldName": oldChapterName,
                                                  "newName": this.value,}),
                        },
                 });
      }
      this.remove()
    }
 }
 item.appendChild(EditChapterTextArea)
}
function selectChapter(chapter){
  if (chapter.parentElement == null){
    return;
  }
  var textAreas = document.getElementsByClassName("EditChapterTextArea")
  if (textAreas.length>0){
    return;
  }
  var SelectedChapters = document.getElementsByClassName("ToCLabel")
  for(var i=0; i<SelectedChapters.length; i++){
      SelectedChapters[i].classList.remove("selected");
  }
  chapter.classList.add("selected");
  document.getElementsByClassName("editIcon")[0].style.display="block";
  notebookName = document.getElementById("notebookName").textContent;
  chapterContent = document.getElementById("chapterContent");
  chapterName = document.getElementById("chapterName");
  chapterName.innerHTML = chapter.textContent;
  chapterContent.innerHTML = tempNotebooks[notebookName][chapter.textContent];
}
function addChapter(item){
  item.style.display = "none";
  addChapterTextArea = item.parentElement.children[1]
  addChapterTextArea.style.display = "block";
}
function createNewChapter(item){
  $.ajax({ type: "POST",
      url: "http://"+window.location.hostname+":5000/notes",
      data: {"entry":"",
             "notebook": document.getElementById("notebookName").textContent,
             "chapter" : item.value,},
  });
  document.getElementById("chapterName").innerHTML = item.value;
  document.getElementById("chapterContent").innerHTML = "";
  item.parentElement.style.display="none"
  item.parentElement.parentElement.children[0].style.display="block";
  ToC = document.getElementsByClassName("ToC")[0]
  tocListItem = document.createElement("li")
  tocListItem.className="ToCLabel hover-red";
  tocListItem.onmouseenter = function () {chapterMouseIn(this)}
  tocListItem.onmouseleave = function () {chapterMouseOut(this)}
  tocListItem.onclick = function () {selectChapter(this)}
  tocListSpan = document.createElement("span")
  tocListSpan.className = "ToCLabelText";
  tocListSpan.innerHTML = item.value
  tocListItem.appendChild(tocListSpan)
  ToC.appendChild(tocListItem)
  item.value = ""
}

function selectNoteBook(notebook, event){
  // dont click when edit is going on!
  var textAreas = document.getElementsByClassName("EditNotebookTextArea")
  if (textAreas.length>0){
    return;
  }

  selectedNoteBookName = notebook.childNodes[0].textContent
  document.getElementsByClassName("editIcon")[0].style.display="block";
  var allLabels = document.getElementsByClassName("notebookLabel")
  Array.from(allLabels).forEach((label) => {
    label.classList.remove("selected")
  })
  if(notebook.classList.contains("selected")){
    notebook.classList.remove("selected");
  }else{
    notebook.classList.add("selected");
  }
  var tocContent = document.getElementById("tocContent");
  var tocList = document.createElement("ol")
  tocList.className = "ToC";
  Array.from(Object.keys(tempNotebooks[selectedNoteBookName]).sort()).forEach(tocItem =>{
    var tocListItem = document.createElement("li")
    tocListItem.className="ToCLabel hover-red";
    tocListItem.onmouseenter = function () {chapterMouseIn(this)}
    tocListItem.onmouseleave = function () {chapterMouseOut(this)}
    tocListItem.onclick = function () {selectChapter(this)}
    tocListItem.ondblclick = function () {editChapterName(this)}
    tocListSpan = document.createElement("span")
    tocListSpan.className = "ToCLabelText";
    tocListSpan.innerHTML = tocItem
    tocListItem.appendChild(tocListSpan)
    tocList.appendChild(tocListItem)
  })
  tocContent.innerHTML = "";
  tocContent.appendChild(tocList)
  // add new chapter
  var AddChapter = document.createElement("ol")
  var AddChapterItem = document.createElement("li")
  AddChapter.className = "addToC"
  AddChapterItem.className = "ToCLabel hover-red"
  AddChapterItem.innerHTML = "+ add new chapter"
  AddChapterItem.onclick = function(){addChapter(this)}
  //add textarea and hide it
  var AddChapterBullet = document.createElement("li")
  AddChapterBullet.className = "ToCLabel hover-red"
  AddChapterBullet.style.display = "none"
  var AddChapterTextArea = document.createElement("textarea")
  AddChapterTextArea.className = "addChapterTextArea"
  AddChapterTextArea.style.resize = "none"
  AddChapterTextArea.cols = "15"
  AddChapterTextArea.rows = "1"
  AddChapterTextArea.onkeypress=function(){
    var key = window.event.keyCode;
    if (key === 13) {createNewChapter(this)}
  }
  AddChapterBullet.appendChild(AddChapterTextArea)

  AddChapter.appendChild(AddChapterItem)
  AddChapter.appendChild(AddChapterBullet)
  tocContent.appendChild(AddChapter)
  var notebookName = document.getElementById("notebookName");
  notebookName.innerHTML = selectedNoteBookName;
  selectChapter(tocList.childNodes[0])
}
function addNotebook(item){
  // hide the text, and display the textArea box...
  item.children[0].style.display="none";
  item.children[1].style.display="block";
}
function createNewNotebook(item){
  var noteBookName = item.value.trim();
  if(noteBookName.length == 0){
    window.alert("input field can not be empty!");
    return false;
  }
  $.ajax({ type: "POST",
      url: "http://"+window.location.hostname+":5000/notes",
      data: {"entry":"",
             "notebook": noteBookName,
             "chapter" : "Chapter 1",},
  });
  var notebookLabels = document.getElementsByClassName("notebookLabels")[0]
  var Label = document.createElement("div")
  Label.className = "notebookLabel"
  Label.onclick = function(){selectNoteBook(this)}
  Label.innerHTML = item.value
  notebookLabels.insertBefore(Label, notebookLabels.childNodes[notebookLabels.childNodes.length - 2]);
  item.value = ""
  item.style.display="none";
  item.parentElement.children[0].style.display="block";
}
function editEntry(item){
  item.style.display = "none";
  var notebook = document.getElementById("notebookName");
  var chapterContent = document.getElementById("chapterContent");
  var form = document.createElement("form")
  form.action = "javascript:;";

  var textArea = document.createElement("textarea");
  textArea.className = "notebookEntry"
  textArea.style.resize = "none";
  textArea.style.width = "98%";
  textArea.type = "text";
  textArea.rows = Math.floor((((chapterContent.offsetHeight-20)*0.75)/13.3));
  textArea.value = chapterContent.innerHTML;
  form.appendChild(textArea)

  form.onsubmit = function() {
    var notebookEntry = document.getElementsByClassName("notebookEntry")[0].value
    var chapterName = document.getElementById("chapterName").innerHTML
    var notebookName = document.getElementById("notebookName").innerHTML
    $.ajax({ type: "POST",
        url: "http://"+window.location.hostname+":5000/notes",
        data: {"entry":notebookEntry,
               "notebook": notebookName,
               "chapter" : chapterName,},
    });
    document.getElementById("chapterContent").innerHTML = notebookEntry;
    tempNotebooks[notebookName][chapterName]=notebookEntry;
    document.getElementsByClassName("editIcon")[0].style.display = "block";
  }

  var submitButton = document.createElement("input");
  submitButton.type = "submit"
  submitButton.style = "float:right; margin-right: 2%;"
  form.appendChild(submitButton)

  chapterContent.innerHTML = ""
  chapterContent.appendChild(form)
}
function editNoteBook(item){
  var textAreas = document.getElementsByClassName("EditNotebookTextArea")
  if (textAreas.length>0){
    return;
  }
  var oldNoteBookName = item.childNodes[0].textContent;
  item.childNodes[0].textContent = "";
  var EditNBTextArea = document.createElement("textarea")
  EditNBTextArea.className = "EditNotebookTextArea"
  EditNBTextArea.style.resize = "none";
  EditNBTextArea.cols = "14"
  EditNBTextArea.rows = "1"
  EditNBTextArea.value = oldNoteBookName;
  EditNBTextArea.onkeypress=function(){
    var key = window.event.keyCode;
    if (key === 13) {
      this.parentElement.childNodes[0].textContent = this.value;
      tempNotebooks[this.value] = tempNotebooks[oldNoteBookName];

      if(this.value != oldNoteBookName){
        $.ajax({ type: "POST",
                 url: "http://"+window.location.hostname+":5000/notes",
                 data: {"rename":JSON.stringify({"type": "noteBookName",
                                                 "oldName": oldNoteBookName,
                                                 "newName": this.value,}),
                       },
                });
      }
      this.remove()
    }
  }
  item.appendChild(EditNBTextArea)
}
function noteBookMouseIn(item){
  var rect = item.getBoundingClientRect();
  var div = document.createElement("div");
  div.classList.add("NoteBookCloseButton");
  div.style.position = "fixed";
  div.style.left = rect.left-3+"px";
  div.style.top = rect.top-5+"px";
  div.onclick = function deleteNotebook(){
    var decision = confirm("you are permenently deleting a notebook! are you sure?");
    if(decision == true){
      var noteBookName = this.parentElement.childNodes[0].textContent
      // send an ajax to delete the the notebook
      $.ajax({ type: "POST",
          url: "http://"+window.location.hostname+":5000/notes",
          data: {"notebook": noteBookName,
                 "action" : "delete",},
      });
      this.parentElement.remove();
    }

  }
  var closeButton = document.createElement("i");
  closeButton.classList.add("fa")
  closeButton.classList.add("fa-times")
  closeButton.style.color="black";
  div.appendChild(closeButton);
  item.appendChild(div);
}

function noteBookMouseOut(item){
  var closButtons = document.getElementsByClassName("NoteBookCloseButton")
  for (var i=0; i<closButtons.length; i++){
    closButtons[i].remove();
  }
}
function chapterMouseIn(item){
  var cross = document.createElement("i");
  cross.classList.add("fa")
  cross.classList.add("fa-times")
  cross.style.color="white";
  cross.style.marginLeft = "10px";
  cross.classList.add("chapterCloseButton");
  cross.onclick=function deleteChapter(){
    chapterName=item.textContent;
    noteBookName=document.getElementById("notebookName").innerHTML;
    var decision = confirm("you are permenently deleting a chapter! are you sure?");
    if(decision == true){
      console.log("deleting chapter:", chapterName, "from notebook:", noteBookName,)
      $.ajax({ type: "POST",
          url: "http://"+window.location.hostname+":5000/notes",
          data: {"notebook": noteBookName,
                 "chapter": chapterName,
                 "action" : "delete",},
      });
      this.parentElement.remove();
      //reset the notebook to select the first present item!
      delete tempNotebooks[noteBookName][chapterName]
      selectNoteBook(document.getElementsByClassName("selected")[0])

    }
  }
  item.appendChild(cross)
}
function chapterMouseOut(item){
  var closButtons = document.getElementsByClassName("chapterCloseButton")
  for (var i=0; i<closButtons.length; i++){
    closButtons[i].remove();
  }
}

function setupSearchPage(){
  window.alert("search is not implemented yet!")
}
