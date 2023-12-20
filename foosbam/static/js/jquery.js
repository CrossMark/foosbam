// Toggle the navbar when clicked
$(document).ready(function() {
// Check for click events on the navbar burger icon
    $(".navbar-burger").click(function() {
        // Toggle the "is-active" class on both the "navbar-burger" and the "navbar-menu"
        $(".navbar-burger").toggleClass("is-active");
        $(".navbar-menu").toggleClass("is-active");
    });
});

// Close the notifations when clicked on the little cross
$(document).ready(function() {
// Check for click events on delete icon
    $(".delete").click(function() {
        // Remove "notification"
        $(".notification").remove();
    });
});
