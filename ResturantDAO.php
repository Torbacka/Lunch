<?php
require "configuration.php"; 

class ResturantDAO{
	
	$place_id_samtrafiken = "ChIJVVVV6WCdX0YRC0rrPp8ib6Q";

	function getPlaceId($id){
	    if(!($mysqli = mysqli_connect(DB_HOST,DB_USER,DB_PASSWORD, DB_NAME))){
	        echo "Det här gick ju inte så bra!";
	    }
	    if($stmt = $mysqli->prepare("SELECT place_id FROM restaurant_info WHERE id = ?")){
	        $stmt->bind_param("d", $id);
	        $stmt->execute();
	        $stmt->bind_result($place_id);
	        $stmt->fetch();
	        $stmt->close();
	    }
	    $mysqli->close();
	    return $place_id;
	}


	function getNumberOfResturants(){
	    $numberOfRows = 0;
	    if(!($mysqli = mysqli_connect(DB_HOST,DB_USER,DB_PASSWORD, DB_NAME))){
	        echo "Det här gick ju inte så bra!";
	    }
	    if($result = $mysqli->query("SELECT COUNT(*) FROM restaurant_info")){
	            $row = $result->fetch_assoc();
	            foreach($row as $cname => $cvalue){
	                $numberOfRows = $cvalue;
	            }
	    
	        $result->close();
	    }else{
	        echo "Gick inte så bra att göra SELECT COUNT(*)";
	    }
	    $mysqli->close();
	    return $numberOfRows;            
	}


	function load_resturants(){
		
		$placeSearchURL = "https://maps.googleapis.com/maps/api/place/radarsearch/json?location=59.3298875,18.0571345&radius=500&type=restaurant&key=".MAP_KEY;
		$myfile = file_get_contents($placeSearchURL);
		$placesArray = json_decode($myfile);
		var_dump($placesArray->results[0]->geometry);
		
		$mysqli = mysqli_connect(DB_HOST,DB_USER,DB_PASSWORD, DB_NAME);
		if(!$mysqli){
				echo "Det här gick ju inte så bra!";
		}
		$mysqli->query("TRUNCATE restaurants");

		$stmt = $mysqli->prepare("INSERT INTO restaurant_info (place_id, latitud, longitud) VALUES (?,?,?)");
		if(!$stmt){
				echo "Det gick inte så bra att göra prepare";
		}
		$stmt->bind_param("sss", $place_id, $latitud,$longitud); 
		foreach ($placesArray->results as $value) {

			$place_id = $value->place_id;
			$latitud = $value->geometry->location->lat;
			$longitud = $value->geometry->location->lng;
			$stmt->execute();
		
		}
		$mysqli->close();
	}
	function findDistance(){

	}
		
}


?>