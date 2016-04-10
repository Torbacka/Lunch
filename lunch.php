<?php
//sendToHipchat(array("color"=>"green","message"=>"Restaurang MBQ,  4.3 \n mongolianbarbeque.se", "notify"=>true,"message_format"=>"text"));

require_once "ResturantDAO.php"; 
$message = prepareArrayForHipchat();

sendToHipchat($message);

function prepareArrayForHipchat(){

    $resturantDAO = new ResturantDAO;
    $restaurant_id = rand(1,$resturantDAO->getNumberOfResturants());
    $placeDataUrl = "https://maps.googleapis.com/maps/api/place/details/json?placeid=" . 
                    $resturantDAO->getPlaceId($restaurant_id) ."&key=".MAP_KEY;
    $placeDataArray = json_decode(file_get_contents($placeDataUrl));
    $hipchatArray = array();
   $message = $placeDataArray->result->name."    avstånd: " . $resturantDAO->getDistance($restaurant_id)." m";
    if(isset($placeDataArray->result->rating)){
       $message .= "      betyg: " . $placeDataArray->result->rating ."\n" ; 
    }else{
        $message .= "\n"; 
    }
    $message .= $placeDataArray->result->website; 
   // $message = "https://maps.googleapis.com/maps/api/staticmap?center=40.714728,-73.998672&zoom=14&size=400x400&key=AIzaSyBSwIaJb7LBn2btW1mcr1fJ-wi-6KZS00M";
    $hipchatArray["color"] = "green";
    $hipchatArray["message"] = "$message";
    $hipchatArray["notify"] = "true";
    $hipchatArray["message_format"] = "text";
    
    
    return $hipchatArray;

}


function sendToHipchat($data){
	$curl = curl_init();
	curl_setopt_array($curl, array(
    		CURLOPT_RETURNTRANSFER => 1,
        		CURLOPT_URL => 'https://samtrafiken.hipchat.com/v2/room/2491579/notification?auth_token='.CHAT_KEY,
    		CURLOPT_POST => 1,
  		CURLOPT_HTTPHEADER => array(
                                            'Content-Type: application/json'
                                           ),
  		CURLOPT_POSTFIELDS => json_encode($data)
	));

	$resp = curl_exec($curl);
	// Close request to clear up some resources
	curl_close($curl);
}

?>

